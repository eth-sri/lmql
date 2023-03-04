document.addEventListener('DOMContentLoaded', (event) => {
  document.querySelectorAll('pre code').forEach((el) => {
    hljs.highlightElement(el);
  });
});

function findParent(el, className) {
  if (!el) return null;
  
  if (el.classList.contains(className)) {
    return el
  } else {
    return findParent(el.parentElement, className)
  }
}

function removeOtherValClassesFromParent(el) {
  let containerBox = findParent(el, "side-by-side")
  if (!containerBox) return;
  Array.from(containerBox.classList)
    .filter(cn => cn.startsWith("val"))
    .forEach(cn => containerBox.classList.remove(cn))
}

function addContainerHoverClass(el) {
  let containerBox = findParent(el, "side-by-side")
  Array.from(el.classList)
      .filter(cn => cn.startsWith("val"))
      .forEach(cn => containerBox.classList.add(cn + "-hover"))
}

function updateHighlight(event) {
  let el = event.target
  if (!el) return;
  if (el.classList.contains("sync")) {
    removeOtherValClassesFromParent(el)
    addContainerHoverClass(el)
  } else {
    removeOtherValClassesFromParent(el)
  }
}

document.addEventListener('pointermove', updateHighlight);
document.addEventListener('pointerleave', updateHighlight);
document.addEventListener('pointerdown', updateHighlight);

window.addEventListener('load', function() {
  // onchange select select-example
  // document.getElementById('select-example').onchange = function() {
  //   var selected = this.options[this.selectedIndex].value;
  //   findParent(this, 'example-selector').querySelectorAll('.side-by-side').forEach(e => e.style.display = 'none');
  //   findParent(this, 'example-selector').querySelectorAll('#' + selected).forEach(e => e.style.display = 'flex');
  //   if (activeAnchor) {
  //     activeAnchor.classList.remove('hover')
  //   }
  // }
})

// select example
window.addEventListener('load', function() {
  function switchToExample() {
    this.parentElement.childNodes.forEach(e => !e.classList || e == this || e.classList.remove('active'))
    this.classList.add('active')
    let selected = this.getAttribute('value')
    findParent(this, 'example-selector').querySelectorAll('.side-by-side').forEach(e => e.style.display = 'none');
    findParent(this, 'example-selector').querySelectorAll('#' + selected).forEach(e => e.style.display = 'flex');

    // set anchor
    let id = selected.substr("precomputed-".length)
    id = id.substr(0, id.length-"-json".length)
    window.location.hash = id
  }
  
  document.querySelectorAll("span.option").forEach(e => e.addEventListener('click', switchToExample))

  // check for anchor 
  let anchor = window.location.hash
  if (anchor) {
    let id = "precomputed-" + anchor.substring(1) + "-json"
    let el = document.querySelectorAll("span.option[value='" + id + "']")[0]
    if (el) {
      el.click()
    }
  }
})

let activeAnchor = null;
function hoverAnchor() {
  if (activeAnchor) {
    activeAnchor.classList.remove('hover')
  }
  activeAnchor = this;
  activeAnchor.classList.add('hover')
}

// sticky hover
window.addEventListener('load', function() {
  // only enable sticky hover on non-touch devices and not (@media only screen and (max-width: 320pt) {)
  if (!window.matchMedia("(hover: none)").matches && !window.matchMedia("(max-width: 320px)").matches) {
    console.log("enabling sticky hover")
    document.querySelectorAll('anchor').forEach(e => e.addEventListener('mouseover', hoverAnchor))
  }
  document.body.addEventListener('click', function() {
    if (activeAnchor) {
      activeAnchor.classList.remove('hover')
    }
  })
})

// check for local dev
window.addEventListener('load', function() {
  // check localhost
  if (window.location.hostname == 'localhost' || window.location.hostname == '127.0.0.1') {
    document.querySelector("#playground-link").href = "http://localhost:3000"
  }
})