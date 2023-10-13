import hljs from 'highlight.js/lib/core'
import lmql from './lmql.hl'
import grammar from './grammar.hl'
import { pd, StringDOMElement } from 'promptdown/promptdown'

hljs.registerLanguage('lmql', lmql)
hljs.registerLanguage('grammar', grammar)

export function highlight(str, lang) {
  let params = {}

  // strip leading lines that are of structure <param>::
  let lines = str.split("\n")
  while (lines.length > 0 && (lines[0].match(/^[a-zA-Z0-9_\-]+::.*/) || lines[0].trim() == "")) {
    let parts = lines[0].split("::")
    if (parts[0] != "") {
      if (parts.length == 2) {
        params[parts[0]] = parts[1] || true
      } else {
        params[parts[0]] = true
      }
    }
    lines.shift()
  }

  str = lines.join("\n")

  if (lang == 'lmql') {
    let result = hljs.highlight(str, { language: "lmql", ignoreIllegals: true }).value;
    result = highlight_inline_lmql_delimiters(result);
    return pre_with_lines(lang, result, params.controls);
  }

  if (lang == "promptdown") {
    let lines = str.split("\n")
    // check and remove lines with min-height::
    let min_height = null
    if (lines[0].trim() == "") {
      lines.shift()
    }
    if (lines[0].startsWith("min-height::")) {
      min_height = lines[0].replace("min-height::", "").trim()
      lines.shift()
    }
    str = lines.join("\n")

    let animated = str.endsWith("[:replay]\n")
    str = str.replace("[:replay]\n", "")

    let d = new StringDOMElement("pre")
    d.classList.add("promptdown")
    d.classList.add("promptdown-compiled")
    if (animated) {
      d.setAttribute("animate", "true")
    }
    pd(d, str, true);
    if (animated) {
      let b = new StringDOMElement("button")
      b.innerText = "↺ Replay"
      b.classList.add("promptdown-button-replay")
      b.setAttribute("onclick", "pd(this.parentElement)")
      d.appendChild(b)
      d.setAttribute("pd-text", d.getAttribute("pd-text") + "[:replay]")
    } else {
      d.setAttribute("pd-text", d.getAttribute("pd-text"))
    }
    if (min_height) {
      d.style["min-height"] = min_height
    }

    return d.toHTML()
  }

  let result = hljs.highlightAuto(str).value
  result = result.replace("&#x27;&#x27;&#x27;lmql", "<span style='opacity: 0.4'>&#x27;&#x27;&#x27;lmql</span>");
  return pre_with_lines("", result, params.controls);
}

function highlight_inline_lmql_delimiters(str) {
  // find '''lmql ... '''\n
  let re = /(&#x27;&#x27;&#x27;lmql)([\s\S]*?)(&#x27;&#x27;&#x27;)/g;
  // replace with "REMOVED"
  str = str.replace(re, "<span class='inline-lmql-delim'>$1</span>$2<span class='inline-lmql-delim'>$3</span>");
  
  return str
}

function pre_with_lines(lang, result, controls = false) {
  let lines = result.split("\n");
  // remove empty lines at start or end
  while (lines.length > 0 && lines[0].trim() == "") {
    lines.shift();
  }
  while (lines.length > 0 && lines[lines.length - 1].trim() == "") {
    lines.pop();
  }

  // check for window controls
  if (controls) {
    result = '<div class="window-controls"><div class="window-control window-control-close"></div><div class="window-control window-control-minimize"></div><div class="window-control window-control-maximize"></div></div>' + result;
  }

  // check for 'grammar' language inline links
  result = linkGrammar(result);
  
  // unescape {-{
  result = result.replace(/\{\{/g, "<span v-pre>{{</span>")

  return '<pre class="hljs"><code><span class="line">' + result + '</span></code></pre>';
}

function linkGrammar(s) {
  // find markdown links [...](...) and replace them by <a>...</a>
  let re = /\[&lt;([^\]]*)\]\(([^)]*)\)/g;
  let m;
  while ((m = re.exec(s)) !== null) {
    // This is necessary to avoid infinite loops with zero-width matches
    if (m.index === re.lastIndex) {
      re.lastIndex++;
    }
    s = s.replace(m[0], `<a href="#${m[2]}">&lt;${m[1]}</a>`);
  }

  return s;
}