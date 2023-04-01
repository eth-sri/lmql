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
    findParent(this, 'example-selector').querySelectorAll('.side-by-side').forEach(e => {
      e.style.display = 'none';
      e.classList.remove('selected')
    });
    findParent(this, 'example-selector').querySelectorAll('#' + selected).forEach(e => {
      e.style.display = 'flex';
      e.classList.add('selected');
    });

    // set anchor
    let id = selected.substr("precomputed-".length)
    id = id.substr(0, id.length-"-json".length)
    if (id == "joke") {
      // remove hash
      if (window.location.hash != "") {
        history.pushState('', document.title, window.location.pathname);
      }
    } else {
      window.location.hash = id
    }
    let that = this;

    if (!window.matchMedia("(max-width: 1070pt)").matches) {
      window.setTimeout(function() {
        // find first <anchor> in example element
        let anchor = document.querySelector('#' + selected).querySelectorAll('anchor')[0]
        hoverAnchor.call(anchor, null)
      }, 100)
    }
  }
  
  document.querySelectorAll("span.option").forEach(e => e.addEventListener('click', switchToExample))

  // check for anchor 
  let anchor = window.location.hash
  if (anchor) {
    let id = "precomputed-" + anchor.substring(1) + "-json"
    let el = document.querySelectorAll("span.option[value='" + id + "']")[0]
    if (el) {
      el.click()
    } else if (anchor.substring(1) == "screenshot") {
      setScreenshotMode()
    }
  } else {
    document.querySelectorAll("span.option")[0].click()
  }
})

let screenshotMode = false;

function setScreenshotMode() {
  screenshotMode = true;
  document.body.classList.add("screenshot-mode")

  let clickDownY = null;
  let clickTop = null;
  let movingEl = null;
  
  document.querySelectorAll("anchor>label .multiline").forEach(e => {
    // on left click position relative top -1pt
    // on right click position relative top 1pt

    e.addEventListener('mousedown', function(event) {
      if (event.button == 0) {
        clickDownY = event.clientY;
        clickTop = parseInt(e.style.top || "0")
        movingEl = e
        event.stopPropagation()
      }
    })
  })

  document.body.addEventListener('mousemove', function(event) {
    if (clickDownY) {
      let delta = event.clientY - clickDownY;
      movingEl.style.top = (clickTop + delta) + "pt"
    }
  })

  document.body.addEventListener('mouseup', function(event) {
    if (clickDownY) {
      event.stopPropagation()
      let delta = event.clientY - clickDownY;
      movingEl.style.top = (clickTop + delta) + "pt"
      clickDownY = null;
      clickTop = null;
      movingEl = null;
    }
  })
}

let activeAnchor = null;
function hoverAnchor() {
  if (activeAnchor && !screenshotMode) {
    activeAnchor.classList.remove('hover')
  }
  activeAnchor = this;
  activeAnchor.classList.add('hover')
}

// sticky hover
window.addEventListener('load', function() {
  // only enable sticky hover on non-touch devices and not (@media only screen and (max-width: 320pt) {)
  if (!window.matchMedia("(hover: none)").matches && !window.matchMedia("(max-width: 320px)").matches) {
    document.querySelectorAll('anchor').forEach(e => e.addEventListener('mouseover', hoverAnchor))
  }
  document.body.addEventListener('click', function() {
    if (activeAnchor) {
      activeAnchor.classList.remove('hover')
    }
    document.querySelectorAll('anchor').forEach(e => e.classList.remove('hover'))
  })
})

function nextAnchor(el) {
  // get anchor-n from class list
  while (el.tagName != "ANCHOR" && el) {
    el = el.parentElement
  }
  let anchorClass = Array.from(el.classList).filter(cn => cn.startsWith("anchor-"))[0]
  let n = parseInt(anchorClass.substr("anchor-".length))
  el = findParent(el, 'side-by-side').querySelector('.anchor-' + (n+1))
  hoverAnchor.call(el, null)
}

function replay(element) {
  // reload contents of <img> tag
  let object = element.parentElement.querySelector('object')
  object.contentDocument.location.reload(true);
}

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    const square = entry.target.querySelector('.square');

    if (entry.isIntersecting) {
      replay(document.getElementById('decoding-animation'))
    }
  });
});

window.addEventListener('load', function() {
  console.log(document.getElementById('decoding-animation'))
  observer.observe(document.getElementById('decoding-animation'))
})