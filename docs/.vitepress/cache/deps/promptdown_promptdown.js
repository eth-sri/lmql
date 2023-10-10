// node_modules/promptdown/promptdown.js
var COLORS = ["blue", "purple", "pink", "magenta", "red", "orange", "lightorange", "yellow", "ochre"];
function strHashCode(str) {
  let hash = 0;
  if (str.length == 0) {
    return hash;
  }
  for (let i = 0; i < str.length; i++) {
    let char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}
function getInsertionPointDFS(el) {
  if (el.nodeType != Node.ELEMENT_NODE) {
    return null;
  }
  if (el.hasAttribute("pd-insertion-point")) {
    return el;
  } else {
    for (let i = 0; i < el.childNodes.length; i++) {
      let ip = getInsertionPointDFS(el.childNodes[i]);
      if (ip) {
        return ip;
      }
    }
  }
  return null;
}
function getPdRoot(el) {
  return el.pdRoot || el;
}
function getInsertionPoint(el) {
  let ip = getInsertionPointDFS(el);
  if (ip)
    ip.pdRoot = el;
  return ip;
}
function clearIp(el) {
  el.removeAttribute("pd-insertion-point");
  el.querySelectorAll(".promptdown-cursor").forEach((c) => c.remove());
}
function setIp(el) {
  el.setAttribute("pd-insertion-point", "true");
}
function appendText(el, text) {
  if (!text)
    return;
  if (text == "↩") {
    let span = new ShadowElement("span");
    span.setAttribute("style", "opacity: 0.2; font-family: monospace;");
    span.classList.add("promptdown-control-character");
    let textChild = new ShadowTextNode("↩");
    span.appendChild(textChild);
    el.appendChild(span);
    return;
  }
  if (el.childNodes.length == 0) {
    el.setAttribute("text", el.getAttribute("text") + text);
    el.appendChild(new ShadowTextNode(text));
  } else {
    let lastChild = el.childNodes[el.childNodes.length - 1];
    if (lastChild && lastChild.nodeType == Node.TEXT_NODE) {
      lastChild.textContent += text;
    } else {
      let textNode = new ShadowTextNode(text);
      el.appendChild(textNode);
    }
  }
}
function getElementType(el) {
  let tagName = el.tagName.toLowerCase();
  if (tagName == "span") {
    if (el.classList.has("promptdown-var-name")) {
      return "var-name";
    } else if (el.classList.has("promptdown-var")) {
      return "var-value";
    } else {
      return tagName;
    }
  } else {
    return tagName;
  }
}
function newVar(ip, instant = false) {
  let span = new ShadowElement("span");
  span.classList.add("promptdown-var");
  span.setAttribute("pd-instant", instant);
  let span_name = new ShadowElement("span");
  span_name.setAttribute("class", "promptdown-var-name");
  setIp(span_name);
  span.appendChild(span_name);
  ip.appendChild(span);
  clearIp(ip);
  return {
    instant: true
  };
}
function removeColorClass(el) {
  Array.from(el.classList).filter((c) => c.startsWith("color-")).forEach((c) => {
    el.classList.remove(c);
  });
}
function runCmd(ip) {
  let cmd = ip.childNodes[0].innerText;
  let params = Array.from(ip.childNodes).slice(1).map((c) => c.textContent).join("");
  if (cmd == "wait") {
    return {
      instant: true,
      cmd: "wait",
      time: parseFloat(params)
    };
  } else if (cmd == "begin") {
    let div = new ShadowElement("p");
    div.classList.add("promptdown-container");
    div.style.display = "inline";
    setIp(div);
    div.setAttribute("id", params);
    clearIp(ip.parentNode);
    ip.parentNode.appendChild(div);
    return {
      instant: true
    };
  } else if (cmd == "end") {
    if (ip.parentNode.getAttribute("id") == params) {
      clearIp(ip.parentNode);
      setIp(ip.parentNode.parentNode);
      return {
        instant: true
      };
    }
  } else if (cmd == "fade") {
    let root = getPdRoot(ip);
    let el = root.querySelector("#" + params);
    if (el) {
      el.classList.add("faded");
    }
  } else if (cmd == "hide") {
    let root = getPdRoot(ip);
    let el = root.querySelector("#" + params);
    if (el) {
      el.style.display = "none";
    }
  }
  return {
    instant: true,
    cmd: ip
  };
}
function getArgs(name) {
  let argument_values = {};
  if (name.includes("(")) {
    let match = name.match(/([^(]+)\(([^)]*)\)/);
    if (match) {
      name = match[1];
      let args = match[2].split(",");
      args.forEach((arg) => {
        let argMatch = arg.match(/([^=]+)=([^=]+)/);
        if (argMatch) {
          let argName = argMatch[1];
          let argValue = argMatch[2];
          argument_values[argName] = argValue;
        }
      });
    }
  }
  argument_values.name = name;
  return argument_values;
}
function latex(pd_text) {
  pd_text = pd_text.replace("[:copy]", "");
  return `\\begin{tcolorbox}[boxrule=0pt, colback=black!5,frame empty]
        ${pd_text.replace(/\[([^\]]+)\|([^\]]+)\]/g, "\\strprm{\\textbf{ $1} $2 }").replace(/\n/g, "\\\\")}
\\end{tcolorbox}`;
}
function copyToClipboard(root, button, as_latex = false) {
  let pdText = root.getAttribute("pd-text");
  if (as_latex)
    pdText = latex(pdText);
  pdText = pdText.replace(/\[:copy\]$/, "");
  pdText = pdText.replace(/↩/g, "");
  navigator.clipboard.writeText(pdText);
  button.innerText = "Copied!";
  window.setTimeout(() => {
    button.innerText = "Copy";
  }, 1e3);
}
function getButton(ip) {
  let name = ip.innerText;
  if (name == "copy") {
    return {
      label: "Copy",
      callback: function(event) {
        let preElement = getPdRoot(ip).el;
        let as_latex = event.altKey;
        copyToClipboard(preElement, this, as_latex);
      }
    };
  }
}
function digest(el, c) {
  let ip = getInsertionPoint(el);
  let elementType = getElementType(ip);
  if (!ip.getAttribute("text")) {
    ip.setAttribute("text", "");
  }
  let instant = ip.getAttribute("pd-instant") == "true";
  let nextIsInstant = ip.getAttribute("pd-next-is-instant") == "true";
  if (ip.getAttribute("pd-next-is-instant")) {
    ip.removeAttribute("pd-next-is-instant");
  }
  if (c == "!") {
    ip.setAttribute("pd-next-is-instant", "true");
    return {
      instant: true
    };
  }
  if (c == "\\") {
    ip.setAttribute("pd-next-is-escaped", "true");
    return {
      instant: true
    };
  }
  if (ip.getAttribute("pd-next-is-escaped")) {
    ip.removeAttribute("pd-next-is-escaped");
    appendText(ip, c);
    return {
      instant: true
    };
  }
  if (elementType == "h1") {
    if (c == "\n") {
      let p = new ShadowElement("p");
      setIp(p);
      ip.parentNode.insertBefore(p, ip.nextSibling);
      clearIp(ip);
      return {
        instant: true
      };
    } else {
      appendText(ip, c);
      return {
        instant: true
      };
    }
  } else if (elementType == "p") {
    if (c == "[") {
      return newVar(ip, nextIsInstant || instant);
    }
  } else if (elementType == "var-name") {
    if (c == "_" && ip.innerText == "") {
      ip.style.display = "none";
      return {
        instant: true
      };
    } else if (c == "@" && ip.innerText == "") {
      ip.style.display = "none";
      ip.parentNode.setAttribute("pd-cmd", "true");
      ip.parentNode.classList.add("cmd");
      return {
        instant: true
      };
    } else if (c == ":" && ip.innerText == "") {
      if (getPdRoot(ip).getAttribute("animate") == "true") {
        let button = new ShadowButton("↺ Replay");
        button.classList.add("promptdown-button-replay");
        button.addEventListener("click", () => {
          let root = getPdRoot(ip).el;
          pd(root);
          return {
            instant: true,
            cmd: "stop"
          };
        });
        ip.parentNode.appendChild(button);
      }
      ip.style.display = "none";
      ip.setAttribute("pd-component", "true");
      ip.parentNode.classList.add("color-none");
      return {
        instant: true
      };
    } else if (c == ":") {
      if (ip.innerText == "bubble") {
        let div = new ShadowElement("div");
        div.classList.add("promptdown-bubble-container");
        ip.parentNode.parentNode.insertBefore(div, ip.parentNode);
        div.appendChild(ip.parentNode);
        ip.parentNode.classList.add("promptdown-bubble");
        if (getPdRoot(ip).getAttribute("animate") == "true") {
          ip.parentNode.classList.add("animate");
          div.classList.add("animate");
        }
        ip.parentNode.classList.delete("promptdown-var-name");
        removeColorClass(ip.parentNode);
      }
    } else if (c == "|") {
      let parent = ip.parentNode;
      let name = ip.innerText;
      if (name.startsWith("_")) {
        name = name.slice(1);
      }
      let args = getArgs(name);
      if (args.code) {
        ip.parentNode.classList.add("code_in_prompt");
        ip.parentNode.classList.add("color-none");
      }
      ip.innerText = args.name;
      if (parent.classList.has("promptdown-bubble")) {
        let role = ip.innerText.split(":")[1];
        parent.classList.add(role);
        parent.parentNode.classList.add(role);
      } else {
        if (name == "") {
          ip.parentNode.classList.add("color-none");
        } else {
          let color = COLORS[strHashCode(name) % COLORS.length];
          ip.parentNode.classList.add("color-" + color);
        }
      }
      clearIp(ip);
      setIp(parent);
      return {
        instant: true
      };
    } else {
      if (c == "]" && ip.getAttribute("pd-component") == "true") {
        let button = getButton(ip);
        if (button) {
          ip.tagName = "button";
          ip.style.display = "inline-block";
          ip.classList.add(ip.innerText);
          ip.innerText = button.label;
          ip.addEventListener("click", button.callback);
          return {
            instant: true
          };
        }
      }
      appendText(ip, c);
      return {
        instant: true
      };
    }
  } else if (elementType == "var-value") {
    if (c == "]") {
      let parent = ip.parentNode;
      if (parent.classList.has("promptdown-bubble-container")) {
        parent = parent.parentNode;
      }
      parent.setAttribute("pd-ignore-whitespace", "true");
      setIp(parent);
      clearIp(ip);
      if (ip.classList.has("cmd")) {
        return runCmd(ip);
      }
      return {
        instant
      };
    } else if (c == "[") {
      return newVar(ip, instant || nextIsInstant);
    } else {
      appendText(ip, c);
      return {
        instant
      };
    }
  }
  if (c == "#") {
    if (ip.innerText == "") {
      ip.remove();
    }
    let h1 = new ShadowElement("h1");
    setIp(h1);
    el.appendChild(h1);
    clearIp(ip);
    return {
      instant: true
    };
  }
  if (c == " " || c == "\n") {
    if (ip.getAttribute("pd-ignore-whitespace") == "true") {
      ip.removeAttribute("pd-ignore-whitespace");
      appendText(ip, c);
      return {
        instant: true
      };
    }
    appendText(ip, c);
    return {
      instant: true
    };
  }
  appendText(ip, c);
  return {
    instant
  };
}
var SHADOW_ELEMENT_ID = 0;
var ShadowElement = class {
  constructor(el_or_tagname) {
    if (typeof el_or_tagname == "string") {
      this.el = document.createElement(el_or_tagname);
    } else {
      this.el = el_or_tagname;
    }
    this.tagName = this.el.tagName;
    this.attributes = {};
    this._style = {};
    this.classList = /* @__PURE__ */ new Set();
    this.children = [];
    this.nodeType = Node.ELEMENT_NODE;
    this.parentNode = null;
    this.syncedElementId = null;
    this.id = SHADOW_ELEMENT_ID++;
    this.eventListeners = {};
  }
  addEventListener(event, callback) {
    this.eventListeners[event] = callback;
  }
  sync(el = null) {
    el = el || this.el;
    if (!el) {
      throw "No element to sync with";
    }
    el.removeAttribute("pd-insertion-point");
    Object.keys(this.attributes).forEach((name) => {
      el.setAttribute(name, this.attributes[name]);
    });
    Object.keys(this._style).forEach((name) => {
      el.style[name] = this._style[name];
    });
    el.class = "";
    this.classList.forEach((c) => {
      el.classList.add(c);
    });
    let existing_children = Array.from(el.childNodes);
    let mapping = {};
    let not_synced = /* @__PURE__ */ new Set();
    existing_children.forEach((child) => {
      if (child.getAttribute && child.getAttribute("pd-shadow-id")) {
        mapping[child.getAttribute("pd-shadow-id")] = child;
        not_synced.add(child);
      } else if (child.pd_shadow_id) {
        mapping[child.pd_shadow_id] = child;
        not_synced.add(child);
      }
    });
    this.children.forEach((child) => {
      let shadow = mapping[child.id];
      not_synced.delete(shadow);
      if (shadow) {
        child.sync(shadow);
      } else {
        let element = null;
        if (child.tagName == "TEXT") {
          element = document.createTextNode("");
          element.pd_shadow_id = child.id;
        } else if (child.tagName == "BUTTON") {
          element = document.createElement("button");
          element.pd_shadow_id = child.id;
        } else {
          element = document.createElement(child.tagName);
          element.setAttribute("pd-shadow-id", "" + child.id);
        }
        el.appendChild(element);
        child.sync(element);
        element.shadowElement = child;
      }
    });
    Object.keys(this.eventListeners).forEach((event) => {
      el.removeEventListener(event, this.eventListeners[event]);
      el.addEventListener(event, this.eventListeners[event]);
    });
    not_synced.forEach((child) => {
      el.removeChild(child);
    });
  }
  setAttribute(name, value) {
    this.attributes[name] = "" + value;
    if (name == "class") {
      this.classList = new Set(value.split(" "));
    }
  }
  getAttribute(name) {
    return this.attributes[name];
  }
  hasAttribute(name) {
    return this.attributes[name] != void 0;
  }
  removeAttribute(name) {
    delete this.attributes[name];
  }
  get childNodes() {
    return this.children;
  }
  get innerText() {
    return this.children.map((c) => c.innerText).join("");
  }
  set innerText(value) {
    this.children = [new ShadowTextNode(value)];
  }
  get style() {
    return this._style;
  }
  set style(value) {
    this._style = value;
  }
  appendChild(child) {
    this.children.push(child);
    if (child.parentNode) {
      child.parentNode.removeChild(child);
    }
    child.parentNode = this;
  }
  insertBefore(child, ref) {
    if (!ref) {
      this.appendChild(child);
      return;
    }
    let index = this.children.indexOf(ref);
    if (index == -1) {
      throw "Reference node not found";
    }
    this.children.splice(index, 0, child);
    if (child.parentNode) {
      child.parentNode.removeChild(child);
    }
    child.parentNode = this;
  }
  querySelectorAll(selector) {
    if (!selector.startsWith(".")) {
      throw "Only class selectors are supported";
    }
    let className = selector.slice(1);
    let matches = [];
    this.children.forEach((child) => {
      if (child.classList.has(className)) {
        matches.push(child);
      }
      child.querySelectorAll(selector).forEach((c) => {
        matches.push(c);
      });
    });
    if (this.classList.has(className)) {
      matches.push(this);
    }
    return matches;
  }
  querySelector(selector) {
    if (!selector.startsWith("#")) {
      throw "Only id selectors are supported";
    }
    let id = selector.slice(1);
    if (this.attributes.id == id) {
      return this;
    }
    let matches = [];
    this.children.forEach((child) => {
      let match = child.querySelector(selector);
      if (match) {
        matches.push(match);
      }
    });
    if (matches.length == 0) {
      return null;
    }
    return matches[0];
  }
  remove() {
    if (this.parentNode) {
      this.parentNode.children = this.parentNode.children.filter((c) => c != this);
    }
  }
  removeChild(child) {
    this.children = this.children.filter((c) => c != child);
  }
};
var ShadowButton = class extends ShadowElement {
  constructor(label) {
    super("button");
    this.label = label;
    this.eventListeners = {};
  }
  addEventListener(event, callback) {
    this.eventListeners[event] = callback;
  }
  sync(el = null) {
    super.sync(el);
    el.innerText = this.label;
    Object.keys(this.eventListeners).forEach((event) => {
      el.addEventListener(event, this.eventListeners[event]);
    });
  }
};
var ShadowTextNode = class extends ShadowElement {
  constructor(content) {
    super("text");
    this.nodeType = Node.TEXT_NODE;
    this.textContent = content;
  }
  sync(el = null) {
    if (!el) {
      throw "No element to sync with";
    }
    el.textContent = this.textContent;
  }
  get innerText() {
    return this.textContent;
  }
};
function pd(el, text = null, ssr = false) {
  let pd_text = el.getAttribute("pd-text") || el.innerText;
  if (text != null) {
    pd_text = text;
  }
  el.innerText = "";
  el.setAttribute("pd-text", pd_text);
  let animate = el.getAttribute("animate") == "true";
  let speed = animate ? 1e3 / parseFloat(el.getAttribute("animate-speed")) : 0;
  if (isNaN(speed)) {
    speed = 6.66;
  }
  let step_size = parseInt(el.getAttribute("animate-step-size"));
  if (isNaN(step_size)) {
    step_size = 4;
  }
  el = new ShadowElement(el);
  el.setAttribute("animate", animate);
  el.appendChild(new ShadowElement("p"));
  el.childNodes[0].setAttribute("pd-insertion-point", "true");
  el.style.opacity = 1;
  if (animate && !ssr) {
    slowDigest(el, pd_text, speed, 0, step_size);
  } else {
    pd_text.split("").forEach((c) => digest(el, c));
    el.sync();
  }
}
function slowDigest(el, text, timeout, step = 0, step_size = 1) {
  if (!text) {
    el.sync();
    let ip = getInsertionPoint(el);
    clearIp(ip);
    return;
  }
  let change = digest(el, text[0]);
  if (change.cmd == "wait") {
    el.sync();
    window.setTimeout(() => {
      slowDigest(el, text.slice(1), timeout, 0, step_size);
    }, change.time);
    return;
  } else if (change.cmd == "stop") {
    return;
  }
  if (change.instant) {
    slowDigest(el, text.slice(1), timeout, step + 1, step_size);
  } else {
    if (step % step_size == 0) {
      el.sync();
      window.setTimeout(() => {
        slowDigest(el, text.slice(1), timeout, step + 1, step_size);
      }, timeout);
    } else {
      slowDigest(el, text.slice(1), timeout, step + 1, step_size);
    }
  }
}
if (!Node) {
  Node = {
    ELEMENT_NODE: 1,
    TEXT_NODE: 3
  };
}
var Node;
if (!document) {
  document = {
    createElement: function(tagName) {
      return new StringDOMElement(tagName);
    },
    createTextNode: function(text) {
      return new StringDOMElement("text");
    }
  };
}
var document;
var StringDOMElement = class _StringDOMElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.attributes = {};
    this.childNodes = [];
    this.classList = /* @__PURE__ */ new Set();
    this.style = {};
  }
  set innerText(value) {
    this.childNodes = [new _StringDOMElement("text")];
    this.childNodes[0].textContent = value;
  }
  get innerText() {
    return this.childNodes.map((c) => c.innerText).join("");
  }
  getElementType() {
    return this.tagName == "text" ? Node.TEXT_NODE : Node.ELEMENT_NODE;
  }
  setAttribute(name, value) {
    if (name == "class") {
      this.classList = new Set(value.split(" "));
      return;
    }
    this.attributes[name] = value;
  }
  getAttribute(name) {
    if (name == "class") {
      return Array.from(this.classList).join(" ");
    }
    return this.attributes[name];
  }
  removeAttribute(name) {
    delete this.attributes[name];
  }
  appendChild(child) {
    this.childNodes.push(child);
  }
  toHTML(top = true) {
    if (this.tagName == "text") {
      return this.textContent;
    }
    if (top) {
      this.attributes["animate"] = "true";
      this.attributes["__animate"] = "true";
      this.attributes["animate-speed"] = "50";
    }
    let html = `<${this.tagName}`;
    Object.keys(this.attributes).filter((name) => name != "class").forEach((name) => {
      html += ` ${name}="${this.attributes[name]}"`;
    });
    if (this.classList.size > 0) {
      html += ` class="${Array.from(this.classList).join(" ")}"`;
    }
    if (Object.keys(this.style).length > 0) {
      html += ` style="`;
      Object.keys(this.style).forEach((name) => {
        html += `${name}: ${this.style[name]};`;
      });
      html += `"`;
    }
    html += ">";
    this.childNodes.forEach((child) => {
      html += child.toHTML(false);
    });
    html += `</${this.tagName}>`;
    return html;
  }
};
export {
  StringDOMElement,
  pd
};
//# sourceMappingURL=promptdown_promptdown.js.map
