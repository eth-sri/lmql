<!--.vitepress/theme/MyLayout.vue-->
<script setup>
// // custom version switcher (maps between /docs/ and /docs/latest/)
function switchVersion(e) {
    // get event via this
    //
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
}

const isLatest = window.location.href.includes("latest")
</script>

<template>
  <div id="version-switcher">
    <label>API:</label>
    <!-- set version.active if /latest in URL -->
    <a :class="{active: !isLatest}" class="version" href="#" @click="switchVersion">Release</a>
    <a :class="{active: isLatest}" class="version" href="#" @click="switchVersion"><code>main</code></a>
  </div>
</template>