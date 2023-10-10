import { createContentLoader } from 'vitepress'
import { createMarkdownRenderer } from 'vitepress'
const config = global.VITEPRESS_CONFIG;

export default createContentLoader('features/*.md', {
  includeSrc: true,
  render: true,
  excerpt: true,
  async transform(rawData) {
    rawData = rawData.filter(page => !page.url.split('/').pop().startsWith('_'))

    let r = await rawData.map(async (page) => {
        // split on '<div class="language-'
        let description = page.src.split('%SPLIT%')[0]
        let code_snippet = page.src.split('%SPLIT%')[1] || ""

        const md = await createMarkdownRenderer(
          config.srcDir,
          config.markdown,
          config.site.base,
          config.logger
        )
        description = md.render(description)
        code_snippet = code_snippet ? md.render(code_snippet) : "";

        return {
          snippet: code_snippet,
          description: description,
          title: page.frontmatter.title,
          template: page.frontmatter.template,
          new: page.frontmatter.new
        }
      })
    return Promise.all(r)
  }
})
