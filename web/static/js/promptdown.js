class Cursor {
    constructor(limit, config, state) {
        this.offset = 0;
        
        this.limit = limit;
        
        this.truncated = false;
        this.config = config;

        this.state = state || {};
    }

    has_capacity() {
        return this.offset < this.limit;
    }

    is_hidden_style(element) {
        if (!this.has_capacity()) {
            return "display: none;"
        } else {
            return "";
        }
    }

    immediate(immediate) {
        if (this.has_capacity() && immediate) {
            return new Cursor(1e9, this.config, this.state);
        } else {
            return this;
        }
    }
}

const DEFAULT_CONFIG = {
    animation_offset: 0,
    non_var_immidiate: true,
    animate: true,
    animate_speed: 120,
    color_mappings: {},
    pallette: ["blue", "purple", "pink", "magenta", "red", "orange", "lightorange", "yellow", "ochre"],
    same_var_same_color: true,
}

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
    return hash;
}

class ScrollState {
    constructor(config) {
        this.config = config;
    }

    var_color(element) {
        if (element.var.length == 0) {
            return "none"
        }
        if (element.metadata && element.metadata.color) {
            return element.metadata.color;
        }
        if (element.var in this.config.color_mappings) {
            return this.config.color_mappings[element.var];
        } else if (this.config.same_var_same_color) {
            let color = this.config.pallette[Math.abs(strHashCode(element.var)) % this.config.pallette.length];
            this.config.color_mappings[element.var] = color;
            return color;
        } else {
            return this.config.pallette[Math.abs(strHashCode(element.var + element.metadata.id)) % this.config.pallette.length];
        }
    }

    extra_element_classes(element, className = null) {
        className = className || "";
        if (element.metadata.environments) {
            for (let e of element.metadata.environments) {
                if (this["hide-" + e]) {
                    className += " cmd-hidden";
                }
                if (this["fade-" + e]) {
                    className += " faded";
                }
            }
        }
        return className;
    }
}

function render_bubble(element, cursor_state) {
    let className = element.var.split(":")[1];
    
    cursor_state = cursor_state.immediate(element.metadata.immediate);
    className += cursor_state.config.animate ? " animate" : "";

    let has_non_text_content = element.content.some((c) => c.var || c.content);
    className += has_non_text_content ? " rich-content" : "";

    return `<div class="promptdown-bubble-container ${cursor_state.state.extra_element_classes(element, className)}" id="el-${element.metadata.id}-bubble-container" style="${cursor_state.is_hidden_style(element)}"><span class="promptdown-bubble ${className}" id="el-${element.metadata.id}-bubble"><span class="promptdown-bubble-content" id="el-${element.metadata.id}-bubble-content">${render(element.content, cursor_state)}</span></span></div>`
}

function run_command(element, cursor_state) {
    if (!cursor_state.has_capacity()) {
        return `<span class="command hidden" id="el-${element.metadata.id}-command" style="${cursor_state.is_hidden_style(element)}">${render_cursor()}</span>`;
    }

    let cmd_key = "ran-" + element.metadata.id;

    if (element.var == "@wait" && !cursor_state.state[cmd_key]) {
        if (!cursor_state.state.config.animate) {
            return `<span class="command hidden" id="el-${element.metadata.id}-command" style="${cursor_state.is_hidden_style(element)}">${render_cursor()}</span>`;
        }

        let timeout = parseInt(element.content);
        
        cursor_state.sleep = timeout;
        cursor_state.offset += 1e9;

        cursor_state.state["ran-" + element.metadata.id] = true;

        return `<span class="command" id="el-${element.metadata.id}-command" style="display: inline-block;">${render_cursor()}</span>`;
    } else if (element.var == "@hide" && !cursor_state.state[cmd_key]) {
        cursor_state.state["hide-" + element.content] = true;
        cursor_state.state["ran-" + element.metadata.id] = true;
    } else if (element.var == "@fade" && !cursor_state.state[cmd_key]) {
        cursor_state.offset += 1e9;
        cursor_state.state["fade-" + element.content] = true;
        cursor_state.state["ran-" + element.metadata.id] = true;
    }

    return `<span class="command hidden" id="el-${element.metadata.id}-command" style="${cursor_state.is_hidden_style(element)}">${render_cursor()}</span>`;
}

function render_heading(element, cursor_state) {
    let title = element.content;
    let tag = "h1"
    if (title.startsWith("##")) {
        tag = "h3";
        title = title.substring(2);
    } else if (title.startsWith("#")) {
        tag = "h2";
        title = title.substring(1);
    }

    return `<${tag} class="promptdown-heading" id="el-${element.metadata.id}-heading" style="${cursor_state.is_hidden_style(element)}">${render(title, cursor_state.immediate(true))}</${tag}>`
}

function render_var(element, cursor_state) {
    if (element.var.startsWith("bubble:")) {
        return render_bubble(element, cursor_state);
    }
    if (element.var.startsWith("@")) {
        return run_command(element, cursor_state);
    }
    if (element.var == "#") {
        return render_heading(element, cursor_state);
    }

    let var_name = ""
    if (!element.var.startsWith("_") && !element.var == "") {
        var_name = `<span class="promptdown-var-name">${element.var}</span>`;
    }

    cursor_state = cursor_state.immediate(element.metadata.immediate);

    let className = `color-${cursor_state.state.var_color(element)}`;

    className += element.metadata.immediate && cursor_state.state.config.animate ? " animate-immediate" : "";
    className += element.metadata.code ? " code_in_prompt" : "";

    return `<span class="promptdown-var ${cursor_state.state.extra_element_classes(element, className)}" id="el-${element.metadata.id+"-var"}" style="${cursor_state.is_hidden_style(element)}">${var_name}<span class="promptdown-var-content" id="el-${element.metadata.id+"-var-content"}">${render(element.content, cursor_state)}</span></span>`
}

function render_cursor(escape=false) {
    if (!escape) {
        return "<span class='promptdown-cursor'>|</span>";
    }

    return "__cursor__";
}

function escape_text(s) {
    return s
        .replaceAll("[[", "__squared__bracket__open__")
        .replaceAll("]]", "__squared__bracket__close__")
        .replaceAll("||", "__pipe__")
}

function unescape_text(s) {
    return s
        .replaceAll("__squared__bracket__open__", "[")
        .replaceAll("__squared__bracket__close__", "]")
        .replaceAll("__pipe__", "|")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("__cursor__", render_cursor(false));
}

function render_text(s, cursor_state) {
    if (Array.isArray(s)) {
        return s.map((e) => render(e, cursor_state)).join("");
    }

    if (cursor_state.offset + s.length < cursor_state.cursor) {
        cursor_state.offset += s.length;
        s = unescape_text(s);
        return `<span class="t">${s}</span>`;
    } else {
        let before = s.substring(0, cursor_state.limit - cursor_state.offset);
        if (before.length < s.length && before.length > 0) {
            before += render_cursor(true);
        }
        cursor_state.offset += s.length;
        if (cursor_state.offset > cursor_state.limit) {
            cursor_state.truncated = true;
        }

        before = unescape_text(before);

        return `<span class="t">${before}</span>`;
    }
}

function render(element, cursor_state) {
    if (element.var || element.var == "") {
        return render_var(element, cursor_state);
    } else if (element.content || element.content == "") {
        return render_text(element.content, cursor_state);
    } else {
        return render_text(element, cursor_state);
    }
}

class Parser {
    constructor(text) {
        this.text = escape_text(text);
        this.offset = 0;
        this.environments = []
    }

    peek() {
        return this.text[this.offset];
    }

    double_peek() {
        return this.offset + 1 < this.text.length ? this.text[this.offset + 1] : null;
    }

    next() {
        return this.text[this.offset++];
    }

    last() {
        return this.offset > 0 ? this.text[this.offset - 1] : null;
    }

    assign_ids(component, ctr) {
        if (component.metadata) {
            component.metadata.id = ctr.i++;
        }
        if (Array.isArray(component.content)) {
            component.content.forEach((c) => this.assign_ids(c, ctr));
        }
    }

    remove_newlines_before_command(components) {
        let result = []
        for (let c of components) {
            if (result.length == 0) {
                result.push(c);
                continue;
            }
            let last = result[result.length - 1];
            let last_content = last.content;
            if (Array.isArray(last_content)) {
                last_content = last_content[last_content.length - 1];
            }
            if (!last_content.endsWith) {
                result.push(c);
                continue;
            }
            if (c.var && c.var.startsWith("@") && last_content.endsWith("\n")) {
                last_content = last_content.substring(0, last_content.length - 1);
                if (Array.isArray(last.content)) {
                    last.content[last.content.length - 1] = last_content;
                } else {
                    last.content = last_content;
                }
            }
            result.push(c);
        }
        return result;
    }

    parse() {
        let components = []
        while (this.text.length > this.offset) {
            if (this.peek() == "#") {
                components.push(this.parse_heading());
            } else if (this.peek() == "[") {
                components.push(this.parse_var());
            } else {
                components.push(this.parse_text());
            }
        }

        // assign ids
        let ctr = {i: 0}
        components.forEach((e, i) => this.assign_ids(e, ctr));

        // remove newlines before commands
        components = this.remove_newlines_before_command(components);
        
        return components;
    }

    parse_text() {
        let content = "";
        while (this.text.length > this.offset && this.peek() != "#" && this.peek() != "[") {
            if (this.peek() == "!" && this.double_peek() == "[") {
                this.next();
                continue
            }
            content += this.next();
        }
        return {
            "content": content,
            "metadata": {}
        }
    }

    expect(c) {
        if (this.peek() != c) {
            let text = this.text.substring(this.offset - 20, this.offset + 20);
            throw new Error("Expected " + c + " but got " + this.peek() + " when parsing \"" + text + "\"");
        }
        this.next();
    }

    parse_heading() {
        let content = "";
        this.expect("#");
        while (this.peek() != "\n") {
            content += this.next();
        }
        this.expect("\n");
        
        return {
            "var": "#",
            "content": content,
            "metadata": {}
        }
    }

    parse_var() {
        let var_name = "";
        let content = [""];
        let immediate = this.last() == "!";

        this.expect("[");
        while (this.peek() != "]" && this.text.length > this.offset) {
            if (this.peek() == "|") {
                this.next();
                var_name = content[0];
                content = [""];
            } else if (this.peek() == "[") {
                let sub_var = this.parse_var();
                content.push(sub_var);
                content.push("")
            } else {
                if (this.peek() == "!" && this.double_peek() == "[") {
                    this.next();
                    continue;
                }
                content[content.length - 1] += this.next();
            }
        }
        this.expect("]");

        
        // remove empty content segments
        content = content.filter((c) => c != "");

        // keep track of environments
        if (var_name == "@begin") {
            this.environments.unshift(content[0]);
        } else if (var_name == "@end") {
            this.environments.shift();
        }

        let metadata = {
            "immediate": immediate
        }

        // if var is of form name("<props>"), extract <props> in quoted string
        let regex = /([_a-zA-Z0-9]+)\(\"([^"]*)\"\)/g;
        let match = regex.exec(var_name);
        if (match) {
            var_name = match[1];
            let props = match[2];
            // parse props as a list of "k1=v1 k2=v2 ..."
            let props_regex = /([_a-zA-Z0-9]+)=([^ ]+)/g;
            let props_match = null;
            while ((props_match = props_regex.exec(props)) != null) {
                metadata[props_match[1]] = props_match[2];
            }
        }

        let v = {
            "var": var_name,
            "content": content,
            "metadata": metadata
        }

        if (this.environments.length > 0) {
            v.metadata["environments"] = Array.from(this.environments);
        }

        return v;
    }
}

function parse(text) {
    let state = "top"; // var, pre-var, heading
    let elements = []

    let active = {
        "var": null,
        "content": "",
        "metadata": {}
    }

    let environment_name = [];
    let cmd_ctr = 0;
    
    for (let c of text) {
        if (state == "top") {
            if (c == "#") {
                if (active.content) {
                    elements.push(active);
                    active = {
                        "var": null,
                        "content": "",
                        "metadata": {}
                    }
                }
                state = "heading";
            } else if (c == "[") {
                let metadata = {}
                if (active.content.endsWith("!")) {
                    metadata["immediate"] = true;
                    active.content = active.content.substring(0, active.content.length - 1);
                }
                if (active.content) {
                    elements.push(active);
                    active = {
                        "var": null,
                        "content": "",
                        "metadata": {}
                    }
                }
                state = "pre-var";
                active.var = "";
                active["metadata"] = metadata;
            } else if (c == "]") {
                return elements;
            } else {
                active.content += c;
            }
        } else if (state == "pre-var") {
            if (c == "|") {
                state = "var";
                active.content = "";
            } else if (c == "]") {
                state = "top";
                active.content = active.var;
                active.var = "";
                elements.push(active);
                active = {
                    "var": null,
                    "content": "",
                    "metadata": {}
                }
            } else {
                active.var += c;
            }
        } else if (state == "var") {
            if (c == "]") {
                state = "top";
                active.content = active.content.trim();
                
                // check for environment commands
                if (active.var == "@begin") {
                    environment_name.unshift(active.content);
                } else if (active.var == "@end") {
                    if (environment_name[0] == active.content) {
                        environment_name.shift();
                    }
                } else if (environment_name.length > 0) {
                    // assign active environment name
                    active.metadata["environment"] = environment_name[0];
                }

                if (active.var.startsWith("@") && 
                    elements.length > 0 && 
                    !elements[elements.length - 1].var &&
                    elements[elements.length - 1].content.endsWith("\n")) {
                    // remove trailing newline before @ command
                    let last_element = elements[elements.length - 1];
                    last_element.content = last_element.content.substring(0, last_element.content.length - 1);
                }

                elements.push(active);
                
                active = {
                    "var": null,
                    "content": "",
                    "metadata": {}
                }
            } else {
                active.content += c;
            }
        } else if (state == "heading") {
            if (c == "\n") {
                state = "top";
                elements.push({
                    "var": "#",
                    "content": active.content,
                    "metadata": {}
                });
                active = {
                    "var": null,
                    "content": "",
                    "metadata": {}
                }
            } else {
                active.content += c;
            }
        }
    }

    if (active.content) {
        elements.push(active);
    }

    // assign ids
    elements.forEach((e, i) => { e.metadata.id = i;});

    return elements;
}

function updateDOM(el, updatedHTML) {
    let div = null;
    if (typeof updatedHTML == "string") {
        div = document.createElement('pre');
        div.innerHTML = updatedHTML;
    } else {
        div = updatedHTML;
    }

    if (div.hasAttribute("style")) {
        el.setAttribute("style", div.getAttribute("style"));
    }

    if (div.hasAttribute("class")) {
        el.className = div.className;
    }
    
    el.childNodes.forEach((node, i) => {
        let id = node.id;
        if (id) {
            let new_node = div.querySelector("#" + id);
            if (new_node) {
                updateDOM(node, new_node);
            }
        } else if (node.classList.contains("t")) {
            let new_node = div.childNodes[i];
            node.innerHTML = new_node.innerHTML;
        }
    });
}

function pd(el, config = null) {
    config = Object.assign(DEFAULT_CONFIG, config || {});
    el.style.opacity = 1.0;

    let components = new Parser(el.innerText).parse();
    el.innerHTML = "";

    // animate with request animation frame
    
    if (config.animate) {
        let offset = config.animation_offset;
        let start = new Date().getTime();
        let offset_per_s = config.animate_speed;
        
        let active_animator = {id: 0};
        let animator_counter = 0;

        function animate(state, id) {
            if (active_animator.id != id) {
                return;
            }

            let cursor = new Cursor(offset, config, state);
            let updatedHTML = components
                .map((c) => render(c, cursor))
                .join("")

            if (el.innerHTML == "") {
                el.innerHTML = updatedHTML;
            } else {
                updateDOM(el, updatedHTML);
            }
            
            if (cursor.sleep > 0) {
                start+= cursor.sleep;
            }
            
            window.setTimeout(() => {
                if (cursor.truncated) {
                    offset = (offset_per_s * (new Date().getTime() - start) / 1000);
                    window.requestAnimationFrame(() => animate(state, id));
                }
            }, cursor.sleep || 0);
        }

        function play() {
            start = new Date().getTime();
            offset = config.animation_offset;
            let state = new ScrollState(config);
            el.innerHTML = "";
            active_animator.id = ++animator_counter;
            animate(state, active_animator.id)
        }

        play();
        el.addEventListener('click', play)
        el.play = play;
    } else {
        let state = new ScrollState(config);
        let cursor = new Cursor(1e9, config, state);
        
        // render in two-passes to capture result of back-referencing commands
        let updatedHTML = components
            .map((c) => render(c, cursor))
            .join("")
        cursor = new Cursor(1e9, config, state);
        updatedHTML = components
            .map((c) => render(c, cursor))
            .join("")

        el.innerHTML = updatedHTML;
    }
}

window.addEventListener('load', function() {
    this.document.querySelectorAll('.promptdown').forEach(el => {
        let config = {}
        if (el.hasAttribute("animate")) {
            config.animate = el.getAttribute("animate") == "true";
        }
        if (el.hasAttribute("animate-speed")) {
            config.animate_speed = parseInt(el.getAttribute("animate-speed"));
        }
        if (el.hasAttribute("animate-offset")) {
            config.animation_offset = parseInt(el.getAttribute("animate-offset"));
        }
        pd(el, config);
    });
});