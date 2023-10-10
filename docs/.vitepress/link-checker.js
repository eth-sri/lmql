import fs from 'fs'
import path from 'path'

// check for args
if (process.argv.length < 3) {
    console.log('Usage: node link-checker.js <directory>')
    process.exit(1)
}

const directory = process.argv[2]


function findAllMarkdownFiles(directory) {
    // find all .ipynb files (also recursively)
    const files = []

    function findMarkdown(dir) {
        const items = fs.readdirSync(dir)
        // check if dir is symlink
        const stat = fs.lstatSync(dir)
        if (stat.isSymbolicLink()) {
            return
        }

        for (const item of items) {
            const itemPath = path.join(dir, item)
            const stat = fs.statSync(itemPath)
            if (stat.isDirectory()) {
                findMarkdown(itemPath)
            } else if (item.endsWith('.md')) {
                files.push(itemPath)
            }
        }
    }

    findMarkdown(directory)

    return files
}

console.log(`Checking links in ${directory}...`)
const markdownFiles = findAllMarkdownFiles(directory)

markdownFiles.forEach(file => {
    // read and find all markdown links
    const contents = fs.readFileSync(file, 'utf-8')
    const lines = contents.split('\n')

    let in_grammar_code_block = false

    lines.forEach((line, lineno) => {
        const links = line.match(/\[.*?\]\((.*?)\)/g)
        lineno = lineno + 1

        if (line.includes("```grammar")) {
            in_grammar_code_block = true
        } else if (line.includes("``\n`")) {
            in_grammar_code_block = false
        }

        // do not scan grammar code block (custom page linking)
        if (in_grammar_code_block) {
            return;
        }

        // if in docs/node_modules, ignore
        if (file.includes('docs/node_modules')) {
            return
        }

        if (links) {
            links.forEach(link => {
                // remove markdown formatting
                let url = link.substring(link.indexOf('(') + 1, link.lastIndexOf(')'))
                
                if (url.startsWith("#")) {
                    // ignore internal links
                    return
                }
                if (url.startsWith("https://docs.lmql.ai")) {
                    console.log(`File ${file}:${lineno} contains direct link to docs.lmql.ai: ${url}`)
                    return
                }

                if (url.startsWith("http") || url.startsWith("mailto")) {
                    // ignore external links
                    return
                }

                // if it has # in it, remove it
                if (url.includes('#')) {
                    url = url.substring(0, url.indexOf('#'))
                }

                // replace .html with .md
                if (url.endsWith('.html')) {
                    url = url.replace('.html', '.md')
                }

                let basedir = path.dirname(file)

                if (url.includes("]")) {
                    return;
                }

                if (url.startsWith("/")) {
                    basedir = directory
                    url = url.substring(1)
                }

                // check if url exists
                try {
                    const stat = fs.statSync(path.join(basedir, url))
                    if (!stat.isFile()) {
                        console.log(`File ${file}:${lineno} contains invalid link: ${url}, not a file: ${path.join(basedir, url)}`)
                    }
                } catch (e) {
                    console.log(`File ${file}:${lineno} contains invalid link: ${url}. Could not find ${path.join(basedir, url)}`)
                }
            })
        }
    })
})