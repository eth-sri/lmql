// https://vitepress.dev/guide/custom-theme
import { h } from 'vue'
import Theme from 'vitepress/theme'
import './style.css'
import 'promptdown/promptdown.css'
import {pd} from "promptdown/promptdown"

// custom version switcher (maps between /docs/ and /docs/latest/)
function setupSwitcher(p) {
  let isLatest = window.location.href.includes("latest")
  
  p.innerHTML = `
    <label>Version</label>
    <div class="version${isLatest ? " active" : ""}"><code>main</code></div>
    <div class="version${!isLatest ? " active" : ""}">Release</div>
  `
  const a = p.parentNode.parentNode
  a.href = "" // isLatest ? a.href.replace("latest", "release") : a.href.replace("release", "latest")
  a.addEventListener("click", (e) => {
    e.preventDefault()
    let isLatest = window.location.href.includes("latest")
    let current = window.location.pathname
    // strip of /docs/
    current = current.replace("/docs/", "")
    // strip of /latest/
    current = current.replace("latest/", "")
    // re-route
    if (isLatest) {
      current = "/docs/" + current
    } else {
      current = "/docs/latest/" + current
    }
    window.location.href = current
  })
}

export default {
  extends: Theme,
  Layout: () => {
    return h(Theme.Layout, null, {
      // https://vitepress.dev/guide/extending-default-theme#layout-slots
    })
  },
  enhanceApp({ app, router, siteData }) {
    let plugin = {
      install(app) {
        app.config.globalProperties.$pd = pd
      }
    }
    app.use(plugin)

    // on mount on app
    app.mixin({
      mounted() {
        let switcher = document.querySelector("#version-switcher")
        if (switcher) {
          let isSetup = switcher.getAttribute("data-setup")
          if (isSetup) return
          setupSwitcher(switcher)
          switcher.setAttribute("data-setup", "true")
        }
      }
    })
  }
}