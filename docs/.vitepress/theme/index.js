// https://vitepress.dev/guide/custom-theme
import { h } from 'vue'
import Theme from 'vitepress/theme'
import './style.css'
import 'promptdown/promptdown.css'
import {pd} from "promptdown/promptdown"

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
  }
}