// https://vitepress.dev/guide/custom-theme
import { h } from 'vue'
import Theme from 'vitepress/theme'
import './style.css'
import 'promptdown/promptdown.css'
import {pd} from "promptdown/promptdown"
// import vue component from VersionSwitch
// import VersionSwitch from './VersionSwitch.vue'

import { defineClientComponent } from 'vitepress'

const VersionSwitch = defineClientComponent(() => {
  return import('./VersionSwitch.vue')
})

export default {
  extends: Theme,
  Layout: () => {
    return h(Theme.Layout, null, {
      // https://vitepress.dev/guide/extending-default-theme#layout-slots
      "sidebar-nav-after": () => h(VersionSwitch)
    })
  },
  async enhanceApp({ app, router, siteData }) {
    let plugin = {
      install(app) {
        app.config.globalProperties.$pd = pd
      }
    }
    app.use(plugin)
  }
}