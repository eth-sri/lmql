(function() {
    /** standard color palette. */
    const COLORS = ["blue", "purple", "pink", "magenta", "red", "orange", "lightorange", "yellow", "ochre"];

    /** Simple str-to-hashcode function. */
    function strHashCode(str) {
        let hash = 0;
        if (str.length == 0) {
            return hash;
        }
        for (let i = 0; i < str.length; i++) {
            let char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash);
    }

    /**
     * DFS traversal of the DOM, returning the first element with the `pd-insertion-point` attribute.
     */
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

    /**
     * Returns the root element of the current PromptDown shadow DOM.
     */
    function getPdRoot(el) {
        return el.pdRoot || el;
    }

    /**
     * Finds the current insertion point in the provided root element.
     * 
     * The insertion point is the element where the next character will be appended to.
     * It is marked by the `pd-insertion-point` attribute.
     */
    function getInsertionPoint(el) {
        let ip = getInsertionPointDFS(el);
        if (ip) ip.pdRoot = el;
        return ip;
    }

    /**
     * Unmarks `el` as the current insertion point.
     */
    function clearIp(el) {
        el.removeAttribute("pd-insertion-point");
        el.querySelectorAll(".promptdown-cursor").forEach(c => c.remove());
    }

    /**
     * Marks `el` as the current insertion point.
     */
    function setIp(el) {
        el.setAttribute("pd-insertion-point", "true");
    }

    /**
     * Appends text to the current insertion point.
     * 
     * This means either appending the text to the current text node or creating a new text node
     * if the current insertion point is not a text node.
     */
    function appendText(el, text) {
        if (!text) return;

        if (text == "↩") {
            let span = new ShadowElement("span")
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

    /**
     * Returns the type of the current insertion point.
     * 
     * Possible types are:
     * - h1: The insertion point is inside an h1 element.
     * - p: The insertion point is inside a p element.
     * - var-name: The insertion point is inside a variable name span.
     * - var-value: The insertion point is inside a variable value span.
     */
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

    /**
     * Inserts a new prompt variable at the current `ip` insertion point.
     * 
     * @param {ShadowElement} ip The insertion point.
     * @param {boolean} instant Whether the variable content should be rendered instantly or typed in.
     */
    function newVar(ip, instant=false) {
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
        }
    }

    /**
     * Removes any color- class from a provided element.
     */
    function removeColorClass(el) {
        Array.from(el.classList).filter(c => c.startsWith("color-")).forEach(c => {
            el.classList.remove(c);
        });
    }

    /**
     * Executes the command at the current `ip` insertion point.
     * 
     * Executes the command either by mutating the DOM or by returning a command
     * to the wrapping digestion loop (e.g. slowDigest) in the case of a `wait` command.
     */
    function runCmd(ip) {
        // get first span as cmd name and remaining #text as parameters
        let cmd = ip.childNodes[0].innerText;
        let params = Array.from(ip.childNodes).slice(1).map(c => c.textContent).join("");

        if (cmd == "wait") {
            return {
                instant: true,
                cmd: "wait",
                time: parseFloat(params)
            }
        } else if (cmd == "begin") {
            let div = new ShadowElement("p");
            div.classList.add("promptdown-container");
            div.style.display = "inline"
            setIp(div);
            div.setAttribute("id", params);
            clearIp(ip.parentNode);
            ip.parentNode.appendChild(div);

            return {
                instant: true
            }
        } else if (cmd == "end") {
            // traverse up until we find a container
            if (ip.parentNode.getAttribute("id") == params) {
                clearIp(ip.parentNode);
                setIp(ip.parentNode.parentNode);
                return {
                    instant: true
                }
            }
        } else if (cmd == "fade") {
            let root = getPdRoot(ip);
            let el = root.querySelector("#" + params);
            if (el) {
                el.classList.add("faded");
            }
        } else if (cmd == "hide")  {
            let root = getPdRoot(ip);
            let el = root.querySelector("#" + params);
            if (el) {
                el.style.display = "none";
            }
        }

        return {
            instant: true,
            cmd: ip
        }
    }

    /**
     * Extracts key-value arguments from a variable name expression, e.g. [var(param1=1,param2=2)| ...].
     */
    function getArgs(name) {
        let argument_values = {}

        if (name.includes("(")) {
            // regex match for name and arguments
            let match = name.match(/([^(]+)\(([^)]*)\)/);
            if (match) {
                name = match[1];
                let args = match[2].split(",");
                args.forEach(arg => {
                    let argMatch = arg.match(/([^=]+)=([^=]+)/);
                    if (argMatch) {
                        let argName = argMatch[1];
                        let argValue = argMatch[2];
                        argument_values[argName] = argValue;
                    }
                });
            }
        }

        return argument_values;
    }

    function latex(pd_text) {
        // replace [VAR|content] with \strprm{content}
        // replace \n with \\ in latex

        // \strprm{Instruction} \strdet{Trigger}\\
        // Intermediate State\\
        // \strprm{Instruction} \strdet{Trigger} \strmod{[Intermediate State]} \strprm{Instruction} \strdet{Trigger} \strmod{[ANSWER]} 
        // % \hfill\textcolor{my-full-green}{\Huge\cmark}

        pd_text = pd_text.replace("[:copy]", "");
        
        return `\\begin{tcolorbox}[boxrule=0pt, colback=black!5,frame empty]
            ${pd_text.replace(/\[([^\]]+)\|([^\]]+)\]/g, "\\strprm{\\textbf{ $1} $2 }").replace(/\n/g, "\\\\")}
    \\end{tcolorbox}`
    }

    function copyToClipboard(root, button, as_latex=false) {
        let pdText = root.getAttribute("pd-text");
        if (as_latex) pdText = latex(pdText);
        // remove [:copy]
        pdText = pdText.replace(/\[:copy\]$/, "");
        // remove explicit line breaks
        pdText = pdText.replace(/↩/g, "");
        navigator.clipboard.writeText(pdText);
        button.innerText = "Copied!";
        window.setTimeout(() => {
            button.innerText = "Copy";
        }, 1000);
    }

    function getButton(ip) {
        let name = ip.innerText;

        if (name == "copy") {
            return {
                label: "Copy",
                callback: function(event) {
                    console.log(event)
                    let preElement = getPdRoot(ip).el;
                    // check for alt key
                    let as_latex = event.altKey;
                    copyToClipboard(preElement, this, as_latex);
                }
            };
        }
    }

    /**
     * `digest` transition function, updating a given Shadow DOM character by character,
     * incrementally rendering the provided PromptDown text.
     * 
     * All state is stored in the provided ShadowElement, which is mutated by this function. 
     * This allows us to stream output into the DOM without having to re-render the entire
     * DOM on every change and without maintaining a separate state.
     * 
     * @param {ShadowElement} el The ShadowElement to render the text to.
     * @param {string} c The next character to digest.
     */
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
            }
        }

        // handle backslash escaping
        if (c == "\\") {
            ip.setAttribute("pd-next-is-escaped", "true");
            return {
                instant: true
            }
        }
        if (ip.getAttribute("pd-next-is-escaped")) {
            ip.removeAttribute("pd-next-is-escaped");
            appendText(ip, c);
            return {
                instant: true
            }
        }

        if (elementType == "h1") {
            if (c == "\n") {
                let p = new ShadowElement("p");
                setIp(p);
                ip.parentNode.insertBefore(p, ip.nextSibling);
                clearIp(ip);
                return {
                    instant: true
                }
            } else {
                appendText(ip, c);
                return {
                    instant: true
                }
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
                }
            } else if (c == "@" && ip.innerText == "") {
                ip.style.display = "none";
                ip.parentNode.setAttribute("pd-cmd", "true");
                ip.parentNode.classList.add("cmd");
                
                return {
                    instant: true
                }
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
                        }
                    })
                    ip.parentNode.appendChild(button);
                }
                ip.style.display = "none";
                ip.setAttribute("pd-component", "true");
                ip.parentNode.classList.add("color-none")
                
                return {
                    instant: true
                }
            } else if (c == ":") {
                if (ip.innerText == "bubble") {
                    // insert div container in-between ip.parentNode and ip.parentNode.parentNode
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
                    // remove color- class
                    removeColorClass(ip.parentNode);
                }
            } else if (c == "|") {
                // leave current span and go to parent span with insertion point
                let parent = ip.parentNode;
                let name = ip.innerText;
                if (name.startsWith("_")) {
                    name = name.slice(1);
                }

                // check for variable arguments , e.g. var(param1=1,param2=2)
                let args = getArgs(name);

                if (args.code) {
                    ip.parentNode.classList.add("code_in_prompt");
                    ip.parentNode.classList.add("color-none");
                }

                if (parent.classList.has("promptdown-bubble")) {
                    let role = ip.innerText.split(":")[1];
                    parent.classList.add(role);
                    parent.parentNode.classList.add(role);
                } else {
                    if (name == "") {
                        ip.parentNode.classList.add("color-none");
                    } else {
                        // choose a color
                        let color = COLORS[strHashCode(name) % COLORS.length];
                        ip.parentNode.classList.add("color-" + color);
                    }
                }

                clearIp(ip);
                setIp(parent);
                
                return {
                    instant: true
                }
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
                        }
                    }
                }

                appendText(ip, c);
                return {
                    instant: true
                }
            }
        } else if (elementType == "var-value") {
            if (c == "]") {
                // leave current span and go to parent span with insertion point
                let parent = ip.parentNode;
                // skip bubble container
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
                    instant: instant
                }
            } else if (c == "[") {
                return newVar(ip, instant || nextIsInstant);
            } else {
                appendText(ip, c);
                return {
                    instant: instant
                }
            }
        }

        if (c == "#") {
            // remove potentially empty p element
            if (ip.innerText == "") {
                ip.remove();
            }

            // append new H1 element
            let h1 = new ShadowElement("h1");
            setIp(h1);
            el.appendChild(h1);
            clearIp(ip);
            return {
                instant: true
            }
        }

        // plain white-space is always instant
        if (c == " " || c == "\n") {
            if (ip.getAttribute("pd-ignore-whitespace") == "true") {
                ip.removeAttribute("pd-ignore-whitespace");
                appendText(ip, c);
                return {
                    instant: true
                }
            }

            appendText(ip, c);
            return {
                instant: true
            }
        }

        appendText(ip, c);

        return {
            instant: instant
        }
    }

    let SHADOW_ELEMENT_ID = 0;

    /**
     * Shadow DOM representation of an HTML element/node.
     * 
     * This class is used to represent the DOM structure of the PromptDown output.
     * 
     * Use the `sync` method to sync the shadow DOM with the actual DOM, as anchored by the root
     * element's `el` property.
     */
    class ShadowElement {
        constructor(el_or_tagname) {
            if (typeof el_or_tagname == "string") {
                this.el = document.createElement(el_or_tagname);
            } else {
                this.el = el_or_tagname;
            }
            
            this.tagName = this.el.tagName;
            this.attributes = {};
            this._style = {}
            this.classList = new Set();
            
            this.children = [];
            this.nodeType = Node.ELEMENT_NODE
            this.parentNode = null;

            this.syncedElementId = null;
            
            this.id = SHADOW_ELEMENT_ID++;
            this.eventListeners = {};
        }

        addEventListener(event, callback) {
            this.eventListeners[event] = callback;
        }

        sync(el=null) {
            el = el || this.el;
            if (!el) {
                throw "No element to sync with";
            }
            
            el.removeAttribute("pd-insertion-point");
            Object.keys(this.attributes).forEach(name => {
                el.setAttribute(name, this.attributes[name]);
            })

            Object.keys(this._style).forEach(name => {
                el.style[name] = this._style[name];
            })
            el.class = "";
            this.classList.forEach(c => {
                el.classList.add(c);
            })

            // extract existing children and their shadows
            let existing_children = Array.from(el.childNodes);
            let mapping = {};
            let not_synced = new Set();
            existing_children.forEach(child => {
                if (child.getAttribute && child.getAttribute("pd-shadow-id")) {
                    mapping[child.getAttribute("pd-shadow-id")] = child;
                    not_synced.add(child);
                } else if (child.pd_shadow_id) {
                    mapping[child.pd_shadow_id] = child;
                    not_synced.add(child);
                }
            });
            
            this.children.forEach(child => {
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

            // update event listeners
            Object.keys(this.eventListeners).forEach(event => {
                el.removeEventListener(event, this.eventListeners[event]);
                el.addEventListener(event, this.eventListeners[event]);
            })

            // remove remaining children
            not_synced.forEach(child => {
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
            return this.attributes[name] != undefined;
        }

        removeAttribute(name) {
            delete this.attributes[name];
        }

        get childNodes() {
            return this.children;
        }

        get innerText() {
            return this.childNodes.map(c => c.innerText).join("");
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
            this.children.forEach(child => {
                if (child.classList.has(className)) {
                    matches.push(child);
                }
                child.querySelectorAll(selector).forEach(c => {
                    matches.push(c);
                })
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
            this.children.forEach(child => {
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
                this.parentNode.children = this.parentNode.children.filter(c => c != this);
            }
        }

        removeChild(child) {
            this.children = this.children.filter(c => c != child);
        }
    }

    /**
     * Shadow DOM representation of a button.
     */
    class ShadowButton extends ShadowElement {
        constructor(label) {
            super("button");

            this.label = label;
            this.eventListeners = {};
        }

        addEventListener(event, callback) {
            this.eventListeners[event] = callback;
        }

        sync(el=null) {
            super.sync(el);

            el.innerText = this.label;
            Object.keys(this.eventListeners).forEach(event => {
                el.addEventListener(event, this.eventListeners[event]);
            })
        }
    }

    /**
     * Shadow DOM representation of a text node.
     */
    class ShadowTextNode extends ShadowElement {
        constructor(content) {
            super("text");
            this.nodeType = Node.TEXT_NODE;
            this.textContent = content;
        }

        sync(el=null) {
            if (!el) {
                throw "No element to sync with";
            }
            el.textContent = this.textContent
        }

        get innerText() {
            return this.textContent;
        }
    }

    /**
     * Converts the provided element into a PromptDown canvas, rendering the provided
     * PromptDown text into it.
     * 
     * The element can configure the following attributes:
     * - animate="true|false": Whether to animate the rendering of the text.
     * - animate-speed="number": The number of characters to reveal per second.
     * - animate-step-size="number": The number of characters to reveal per step.
     * 
     * @param {HTMLElement} el The element to render the PromptDown output into.
     */
    function pd(el, text=null) {
        // obtain PromptDown text
        let pd_text = el.getAttribute("pd-text") || el.innerText;
        if (text != null) {
            pd_text = text;
        }

        // reset element
        el.innerText = "";
        el.setAttribute("pd-text", pd_text);
        
        // parse configuration parameters
        let animate = el.getAttribute("animate") == "true" || el.getAttribute("__animate") == "true"
        console.log(el)

        let speed = animate ? 1000.0 / parseFloat(el.getAttribute("animate-speed")) : 0;
        if (isNaN(speed)) {
            speed = 6.66;
        }
        let step_size = parseInt(el.getAttribute("animate-step-size"));
        if (isNaN(step_size)) {
            step_size = 4;
        }

        // create shadow element
        el = new ShadowElement(el);
        el.setAttribute("animate", animate);

        // create default root element
        el.appendChild(new ShadowElement("p"));
        el.childNodes[0].setAttribute("pd-insertion-point", "true");
        
        // animates in element
        el.style.opacity = 1;

        // digest pd_text character by character
        if (animate) {
            // timed animation
            slowDigest(el, pd_text, speed, 0, step_size);
        } else {
            // instant rendering
            pd_text.split("").forEach(c => digest(el, c));
            el.sync();
        }
    }
    /** 
     * Plays a timed animation streaming in the provided text character by character,
     * into the view defined by the provided ShadowElement.
     * 
     * @param {ShadowElement} el The ShadowElement to render the text to.
     * @param {string} text The full text to digest character by character.
     * @param {number} timeout The timeout in-between non-instant characters.
     * @param {number} step The current step in the animation.
     * @param {number} step_size The number of characters to digest in one chunk without waiting in-between.
     */
    function slowDigest(el, text, timeout, step=0, step_size=1) {
        if (!text) {
            el.sync();
            let ip = getInsertionPoint(el);
            clearIp(ip);
            return;
        }
        
        let change = digest(el, text[0]);
        if (change.cmd == "wait") {
            el.sync()
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
                el.sync()
                window.setTimeout(() => {
                    slowDigest(el, text.slice(1), timeout, step + 1, step_size);
                }, timeout);
            } else {
            slowDigest(el, text.slice(1), timeout, step + 1, step_size);
            }
        }
    }

    window.pd = pd;
})();
