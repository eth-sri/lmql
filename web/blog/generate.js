// run node with import support
// node generate.js --experimental-modules

import fs from 'fs';
import jsdom from 'jsdom';
// marked
import * as marked from 'marked';

const index_html = fs.readFileSync("index.template.html")

// read all markdown files in articles/
let articles = fs.readdirSync("../../docs/build/html/blog/")

articles = articles.map((article) => {
    let contents = fs.readFileSync("../../docs/build/html/blog/" + article).toString();
    contents = jsdom.JSDOM.fragment(contents).querySelector("article").innerHTML
    
    return {
        filename: article,
        content: contents,
    }
})
// extract lines with "release: " as timestring
articles = articles.map((article) => {
    // get first <p></p> block
    let metadata_block = article.content.split("<p>")[1].split("</p>")[0]
    let content = article.content.split("</p>").slice(1).join("</p>")

    let data = {
        filename: article.filename.replace(".html", ""),
        content: content,
        release: "",
        authors: "",
    }

    for (let line of metadata_block.split("\n")) {
        if (line.startsWith("metadata:release: ")) {
            data.release = line.substring("metadata:release: ".length)
        } else if (line.startsWith("metadata:authors: ")) {
            data.authors = line.substring("metadata:authors: ".length).split(",")
        } else {
            console.warn("Unknown metadata line: " + line)
        }
    }

    return data
})
// parse release as date
articles = articles.map((article) => ({
    ...article,
    release: new Date(article.release),
}))

// sort articles by release date
articles = articles.sort((a, b) => b.release - a.release)

function template(title, anchor, authors, date, content, startpage) {
    const author_data = {
        "luca": {
            "name": "Luca Beurer-Kellner",
            "link": "https://www.sri.inf.ethz.ch/people/luca",
        },
        "team": {
            "name": "LMQL Team",
            "link": "mailto:hello@lmql.ai",
        },
        "marc": {
            "name": "Marc Fischer",
            "link": "https://www.sri.inf.ethz.ch/people/marc",
        },
        "martin": {
            "name": "Martin Vechev",
            "link": "https://www.sri.inf.ethz.ch/people/martin",
        },
    }

    let author_info = authors.map((author) => {
        const data = author_data[author]
        if (!data) {
            return `<span class="author-block">
            ${author}
            </span>`
        }
        return `<span class="author-block">
            <a href="${data.link}">${data.name}</a>
        </span>`
    }).join(",")
    
    return `<section class="section blog ${startpage ? 'startpage' : ''}" id="${anchor}">
    <div class="container is-max-desktop">
      <!-- Abstract. -->
      <div class="columns is-centered has-text-centered">
        <div class="column">
          <h5 class="title is-2 has-text-left" style="margin-bottom: 2pt;">
            <a href="blog/${anchor}.html" class="anchor">
                ${title}
            </a>
          </h5>
          <div class="content has-text-justified">
          <div class="authors">
            <div class="is-size-5 publication-authors">
              ${author_info}
            </div>
          </div>
            <div class="date">
                ${date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' , year: 'numeric' })}
            </div>
            ${content}
          </div>
        </div>
    </div>
  </section>
    `
}

function getTitle(article) {
    let title = null;
    let lines_without_title = article

    let firstH1 = jsdom.JSDOM.fragment(article.content).querySelector("h1")
    let outerHtml = firstH1.outerHTML
    lines_without_title = article.content.replace(outerHtml, "").split("\n")

    // remove .headerlink from title
    firstH1.querySelector(".headerlink").remove()
    title = firstH1.innerHTML

    return [title, lines_without_title.join("\n")]
}

function render_article(article, startpage) {
    // find and remove first line starting with #
    const [title, content] = getTitle(article)
    let anchor = article.filename

    const html = marked.parse(content)
    return template(title, anchor, article.authors, article.release, html, startpage)
}

function render_page(page) {
    let articles_html = articles
        .filter(a => a.filename == page || page == "index")
        .map(a => render_article(a, page == "index")).join("\n")

    if (page != "index") {
        articles_html += `<a class='blog see-all' href="/blog">See all blog posts</a>`
    }

    let html_output = index_html.toString()
    let article = null;
    if (page != "index") {
        articles.forEach((a) => {
            if (a.filename == page) {
                article = a
            }
        })
    }
    // insert articles
    html_output = html_output.replace("<%ARTICLES%>", articles_html)

    // compute title
    let title = "LMQL Development Blog"
    if (article != null) {
        title = getTitle(article)[0]
    }

    let description = "Regular updates on the LMQL project."
    if (article != null) {
        description = article.content.split("\n").filter((line) => !line.startsWith("#") && line.trim() != "").slice(0, 3).join(" ")
    }

    // replace all <%TITLE%> with title
    html_output = html_output.replace(/<%TITLE%>/g, title)
    // replace all <%DESCRIPTION%> with description
    html_output = html_output.replace(/<%DESCRIPTION%>/g, description)

    // last update date and hour+minute Zurich time
    const now = new Date()
    const formatted = new Date().toLocaleString('en-US', { timeZone: 'Europe/Zurich', weekday: 'short', month: 'short', day: 'numeric' , hour: 'numeric', minute: 'numeric' })
    const timezone = now.toLocaleString('en-US', { timeZoneName: 'short' }).split(' ').pop()
    html_output = html_output.replace("<%LAST_UPDATED%>.", formatted + " (" + timezone + ")")

    fs.writeFileSync(page + ".html", html_output)
}

articles.forEach((article) => {
    render_page(article.filename)
})
render_page("index")
