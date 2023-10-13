import { createContentLoader } from 'vitepress'
import { createMarkdownRenderer } from 'vitepress'
const config = global.VITEPRESS_CONFIG;

export default createContentLoader('features/examples/*.md', {
  includeSrc: true,
  render: true,
  excerpt: true,
  watch: "features/examples/*.md",
  async transform(rawData) {
    let r = await rawData.map(async (page, i) => {
      // split on '<div class="language-'
      let description = page.src.split('%SPLIT%')[0]
      let code_snippet = page.src.split('%SPLIT%')[1] || ""
      let output = page.src.split('%SPLIT%')[2] || ""

      const md = await createMarkdownRenderer(
        config.srcDir,
        config.markdown,
        config.site.base,
        config.logger
      )

      description = md.render(description)
      code_snippet = code_snippet ? md.render(code_snippet) : "";
      output = output ? md.render(output) : "";

      return {
        id: i,
        path: page.url,
        title: page.frontmatter.title,
        description: description,
        code: code_snippet,
        output: output,
      }
    });
    
    return Promise.all(r)
  }
})