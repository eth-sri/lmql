import { defineConfig } from 'vitepress'
import fs from 'fs'
import path from 'path'
import { highlight } from "./highlighter"

const docs_dir = `docs/`
const docs_path = "/" + docs_dir

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "LMQL",
  description: "Language Model Query Language",
  ignoreDeadLinks: true,
  head: [
    [
      "script",
      {
        async: true,
        src: "/promptdown.js"
      }
    ],
    [
      "script",
      {
        async: true,
        src: "https://buttons.github.io/buttons.js"
      }
    ]

  ],
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Blog', link: '/blog/', activeMatch: '^/blog/' },
      { text: 'Research', link: '/research/index.html' },
      { text: 'Docs', link: docs_path, activeMatch: '^' + docs_path },
      { text: '▶ Playground', link: '/playground/', target: '_blank' },
    ],
    search: {
      provider: 'local'
    },
    logo: '/lmql.svg',
    sidebar: createSidebars(),
    socialLinks: [
      { icon: 'github', link: 'https://github.com/eth-sri/lmql' },
      { icon: 'discord', link: 'https://discord.gg/5djae9gJVB' },
    ]
  },
  markdown: {
    defaultHighlightLang: 'lmql',
    highlight: highlight
  }
})

function createSidebars() {
  let sb = {}
  const docsBar = (docs_dir, docs_path) => [
    {
      text: '',
      collapsable: true,
      collapsed: false,
      base: docs_path,
      items: sidebar(docs_dir)
    },
    {
      text: 'Language',
      collapsable: true,
      collapsed: false,
      base: docs_path + 'language',
      items: sidebar(docs_dir + "language")
    },
    {
      text: 'Model Support',
      collapsable: true,
      collapsed: false,
      base: docs_path + 'models',
      items: sidebar(docs_dir + "models")
    },
    {
      text: 'Library',
      collapsable: true,
      collapsed: false,
      base: docs_path + 'lib',
      items: sidebar(docs_dir + "lib")
    },
    {
      text: 'Development',
      collapsable: true,
      collapsed: false,
      base: docs_path + 'development',
      items: sidebar(docs_dir + "development")
    },
    {
      text: '',
      collapsable: false,
      collapsed: false,
      items: [
        {
          text: docs_dir.includes("latest") ? 'Switch to Stable' : 'Switch to Latest',
          link: docs_dir.includes("latest") ? '/docs/' : '/docs/latest/',
          path: docs_dir.includes("latest") ? '/docs/' : '/docs/latest/',
        }
      ]
    },
  ]
  sb["docs/"] = docsBar("docs/", "/docs/")
  sb["docs/latest/"] = docsBar("docs/latest/", "/docs/latest/")
  return sb
}

function frontmatter(content) {
  // parse frontmatter
  let fm = {}
  let lines = content.split("\n")
  if (lines[0].trim() == "---") {
    lines.shift()
    let line = lines.shift()
    while (line.trim() != "---") {
      let parts = line.split(":")
      let key = parts.shift().trim()
      let value = parts.join(":").trim()
      fm[key] = value
      line = lines.shift()
    }
  }
  return fm
}

function sidebar(folder, subdir="") {
  let files = fs.readdirSync(path.resolve(__dirname, '../' + folder))
  const sidebars = []

  // index.md should be the first element
  const index = files.indexOf('index.md')
  if (index > -1) {
    const indexFile = files.splice(index, 1)[0]
    files.unshift(indexFile)
  }

  files = files.filter(file => file.endsWith('.md'))
  
  files = files.map(file => {
    let p = path.resolve(__dirname, `../${folder}/${file}`)
    const content = fs.readFileSync(p, 'utf-8')
    let fm = frontmatter(content)
    
    // find first # title
    const name = content.match(/# (.*)/)[1]

    if (fm.order) {
      try {
        fm.order = parseInt(fm.order)
      } catch (e) {
        console.log(`Error parsing order for ${file}`)
      }
    } else {
      fm.order = 9999;
    }

    return {
      name: name,
      file: file,
      frontmatter: fm
    }
  });

  // sort by frontmatter.order
  files.sort((a, b) => {
    return a.frontmatter.order - b.frontmatter.order
  })

  files.forEach(file_info => {
    let file = file_info.file;
    let name = file_info.name

    let base = file.replace('.md', '') + "/"
    let base_path = folder + "/" + base
    
    let items = []

    // check for base_path 
    if (fs.existsSync(path.resolve(__dirname, `../${base_path}`))) {
      items = sidebar(base_path, base)
      
      sidebars.push({
        text: name,
        link: `/${file}`,
        activeMatch: `^/${subdir}${base_path}`,
        collapsable: true,
        collapsed: true,
        items: items
      })
    } else {
      sidebars.push({
        text: name,
        link: `/${subdir}${file}`
      })
    }
  })

  return sidebars
}