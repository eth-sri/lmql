// posts.data.js
import { createContentLoader } from 'vitepress'

export default createContentLoader('blog/posts/*.md', {
  includeSrc: true, // include raw markdown source?
  render: true,     // include rendered full page HTML?
  excerpt: true,    // include excerpt?
  transform(rawData) {
    return rawData.filter(page => page.url != "/blog/") // filter out the blog index page
    .sort((a, b) => {
        return new Date(b.frontmatter.date) - new Date(a.frontmatter.date)
    })
    .map((page) => {
        return page
    })
  }
})