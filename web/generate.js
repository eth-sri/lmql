// run node with import support
// node generate.js --experimental-modules

import * as qs from "./queries.js"
import {reconstructTaggedModelResult} from "./tagged-model-result.js"
import fs from 'fs';

let queries = []

function parseLMQL(code) {
    const segments = []
    let current_segment = ""
    
    let inDoubleQuote = false;
    let inSingleQuote = false;
    let inTripleQuote = false;
    let stringIndent = "";
    let stringOffset = 0;
    
    let inLineComment = false;
    
    let lineIndent = "";
    let lineOffset = 0;
    let spaceOnlyInLineSoFar = true;
    
    for (let i = 0; i < code.length; i++) {
        // keep track of line indent
        if (code[i] === '\n') {
            lineIndent = "";
            lineOffset = 0;
            spaceOnlyInLineSoFar = true;
        } 
        lineOffset += 1;
        if (spaceOnlyInLineSoFar && code[i] !== '\n') {
            if (code[i] === ' ' || code[i] === '\t') {
                lineIndent += code[i];
            } else {
                spaceOnlyInLineSoFar = false;
            }
        }

        if (i + 2 < code.length && code[i] === '"' && code[i + 1] === '"' && code[i + 2] === '"') {
            i += 2
            if (inTripleQuote) {
                current_segment += '"""'
                inTripleQuote = false
                segments.push({type: "str", content: current_segment, indent: stringIndent, offset: stringOffset})
                current_segment = ""
            } else {
                inTripleQuote = true
                stringIndent = lineIndent;
                stringOffset = lineOffset;
                segments.push({type: "code", content: current_segment})
                current_segment = '"""'
            }
            continue
        } else if (code[i] == '"' && !inTripleQuote && !inSingleQuote) {
            if (inDoubleQuote) {
                current_segment += '"'
                inDoubleQuote = false
                segments.push({type: "str", content: current_segment, indent: stringIndent, offset: stringOffset})
                current_segment = ""
            } else {
                inDoubleQuote = true
                stringIndent = lineIndent;
                stringOffset = lineOffset;
                segments.push({type: "code", content: current_segment})
                current_segment = '"'
            }
        } else if (code[i] == "'" && !inTripleQuote && !inDoubleQuote) {
            if (inSingleQuote) {
                current_segment += "'"
                inSingleQuote = false
                segments.push({type: "str", content: current_segment})
                current_segment = ""
            } else {
                inSingleQuote = true
                stringIndent = lineIndent;
                stringOffset = lineOffset;
                segments.push({type: "code", content: current_segment, indent: stringIndent, offset: stringOffset})
                current_segment = "'"
            }
        } else if (code[i] == "#" && !inTripleQuote && !inDoubleQuote && !inSingleQuote) {
            segments.push({type: "code", content: current_segment})
            inLineComment = true
            current_segment = "#"
        } else if (code[i] == "\n" && inLineComment) {
            inLineComment = false
            segments.push({type: "comment", content: current_segment + "\n"})
            current_segment = ""
        } else {
            current_segment += code[i]
        }
    }
    if (inSingleQuote || inDoubleQuote || inTripleQuote) {
        throw new Error("Code ended in the middle of a string")
    }
    if (current_segment.length > 0) {
        segments.push({type: "code", content: current_segment})
    }
    return segments
}

class GraphNode {
    constructor(data, edges) {
        Object.assign(this, data)
        this.id = data.id
        this.edges = edges
        this.nodesMap = null;
    }

    data(path) {
        path = path.split(".")
        let r = path.reduce((acc, key) => acc[key], this)
        return r
    }

    incomers() {
        return this.edges.filter(e => e[1] === this.id).map(e => this.nodesMap.get(e[0]))
    }
}

function Query(q, showcase_info, id, i) {
    // read and parse q.state json file
    const result = fs.readFileSync("../src/lmql/ui/playground/public/" + q.state)
    const state = JSON.parse(result)
    const decoder = JSON.parse(state["decoder-graph"])
    const nodes = decoder.nodes.map(n => new GraphNode(n, decoder.edges))
    const nodesMap = new Map(nodes.map(n => [n.id, n]))
    nodes.forEach(n => n.nodesMap = nodesMap)

    const variable_indices = new Map()
    let code = q.code.trim()
    // replace < and > with &lt; and &gt;
    code = code.replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    let parsed = parseLMQL(code)

    let keywords = ["argmax", "from", "and", "where", "sample", "beam", "async", "def", "import", "for", "in", "await", "return", "try", "except", "assert", "if", "else", "el", "distribution"]
    for (let k of keywords) {
        parsed = parsed.map(s => {
            if (s.type === "code") {
                return {"type": "code", "content": s.content.replaceAll(k, `<span class="lmql-kw">${k}</span>`)}
            } else {
                return s
            }
        })
    }

    let code_formatted = parsed.map((s) => {
        if (s.type === "str") {
            const max_column_width = 40
            // console.log("string with indent", [s.indent])
            let lines = [""]
            // split by maximum column width
            for (let c of s.content) {
                if (c === '\n') {
                    lines.push("")
                    continue
                }
                if ((lines[lines.length - 1].length > max_column_width || (lines.length == 1 && lines[lines.length - 1].length + s.offset > max_column_width)) && c === " ") {
                    // preprend unicode line broken char
                    lines.push(s.indent + " ➥")
                }
                lines[lines.length - 1] += c
            }
            return `<span class="lmql-str">${lines.join("\n")}</span>`
        }
        if (s.type === "comment") {
            return `<span class="lmql-comment">${s.content}</span>`
        }
        return s.content;
    }).join("")

    // highligh anchors
    if (showcase_info.anchors) {
        Object.keys(showcase_info.anchors).forEach(k => {
            let label = showcase_info.anchors[k]
            if (!code_formatted.includes(k)) {
                console.log(code_formatted)
                console.error(`Anchor ${k} not found in code`)
            }
            if (label.type === "multiline") {
                code_formatted = code_formatted.replace(k, `<anchor>${k}<label><div class="multiline">${label.text}</div><div class="bridge"></div>
                </label><div class="dot"></div></anchor>`)
            } else {
                code_formatted = code_formatted.replace(k, `<anchor>${k}<label><div class="multiline">${label}</div><div class="bridge"></div>
                </label><div class="dot"></div></anchor>`)
            }
        })

        // scan code_formatted via regex for <anchor> and replace with <anchor class="anchor-1">...</anchor>
        let j = 0;
        code_formatted = code_formatted.replaceAll(/<anchor>/g, (match, p1) => {
            return `<anchor class="anchor-${++j}">`
        })
    }

    // enclose all [VAR_NAME] as "<lmql-var class="sync val2">VAR_NAME</lmql-var>"
    let j = 0;
    showcase_info.variables.forEach(v => {
        let index = variable_indices.get(v) || (++j)
        code_formatted = code_formatted.replaceAll(`[${v}]`, `<span class="lmql-var sync val${index}">[${v}]</span>`)
        variable_indices.set(v, index)
    })
    
    // detect https://arxiv links and enclose them as <a href="...">...</a>
    code_formatted = code_formatted.replaceAll(/(https:\/\/arxiv[^\s]+)/g, `<a href="$1" target="_blank">$1</a>`)
    // same but with arxiv links only

    // replace ➥ with grey styled ➥
    code_formatted = code_formatted.replaceAll("➥", `<span style="color: grey">➥</span>`)

    // find node with highest nN value and highest seqlogprob
    let max = 0
    let maxNode = null
    for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i]
        const n = parseInt(node.id.substring(1))
        if (n > max) {
            max = n
            maxNode = node
        }
    }

    let taggedResult = reconstructTaggedModelResult([maxNode])[0]
    let segments = taggedResult.tokens
    // console.log(q.code)

    let model_output = ""
    const prompt = (v) => `<span class="variable-value prompt sync valp">\n${v.replaceAll("\n", "<br/>").replaceAll("\\n", "<br/>")}</span>`
    const varv = (v, name, i) => `<span class="variable-value sync val${i}">
    <span class="badge">${name}</span>
    ${v.replaceAll("\n", "<br/>").replaceAll("\\n", "<br/>")}
</span>`

    for (let s of segments) {
        s.content = s.content.replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    }

    if (showcase_info.truncate_output) {
        segments[0] = {variable: "__prompt__", content: "<span class='lmql-truncated'>...</span>" + segments[0].content.substring(showcase_info.truncate_output)}
    }

    for (let s of segments) {
        if (s.variable == "<eos>") {
            continue
        }
        if (s.variable == "__prompt__") {
            model_output += prompt(s.content) + "\n"
        } else {
            // get s.variable before the [idx]
            let vname = s.variable.split("[")[0]
            if (showcase_info.variables.includes(vname)) {
                model_output += varv(s.content, vname, variable_indices.get(vname)) + "\n"
            } else {
                model_output += prompt(s.content) + "\n"
            }
        }
    }

    if (showcase_info["extra-output"]) {
        if (showcase_info["extra-output"].startsWith("<clear/>")) {
            model_output = ""
            showcase_info["extra-output"] = showcase_info["extra-output"].substring("<clear/>".length)
        }
        model_output += showcase_info["extra-output"]
    }

    const compactClass = showcase_info["compact"] ? " compact" : ""

    const template = `
<div id="${id}" class="side-by-side${compactClass} ${i == 0 ? 'first' : ''}">
    <div class="query">
        <h3>
            LMQL
            <a href="playground#${id.replaceAll("precomputed-", "").replaceAll("-json", "")}" target="_blank">
            Open In Playground
            </a>
        </h3>
        <pre>
${code_formatted}
        </pre>
    </div>
    <div class="output" ${showcase_info["output-style"] ? `style="${showcase_info["output-style"]}"` : ""}>
        <h3>Model Output</h3>
        ${model_output}
        <span class='legend'>Highlighted text is model output.</span>
    </div>
</div>`
    return template
}

const showcase = JSON.parse(fs.readFileSync("showcase-queries.json"))
const saved_queries = qs.default.queries
let q_text = ""
let i = 0;
for (let category of saved_queries) {
    for (let q of category.queries) {
        if (q.state in showcase) {
            let id = q.state.replaceAll("/", "-").replaceAll(".", "-")
            q_text += Query(q, showcase[q.state], id, i++)
            i += 1
            queries.push({
                "name": q.name || "Untitled",
                "id": id,
            })
        } else {
            console.log("Skipping " + q.state)
        }
    }
}

const index_html = fs.readFileSync("index.template.html")
let index_html_output = index_html.toString().replace("<%SAMPLES%>", q_text)
let query_options = queries.map((q,i) => `<span class="option ${i==0?'active':''}" value="${q.id}">${q.name}</span>`).join("\n")
index_html_output = index_html_output.replace("<%SAMPLES_LIST%>", query_options)
// last update date and hour+minute Zurich time
const now = new Date()
const formatted = new Date().toLocaleString('en-US', { timeZone: 'Europe/Zurich', weekday: 'short', month: 'short', day: 'numeric' , hour: 'numeric', minute: 'numeric' })
const timezone = now.toLocaleString('en-US', { timeZoneName: 'short' }).split(' ').pop()
index_html_output = index_html_output.replace("<%LAST_UPDATED%>.", formatted + " (" + timezone + ")")

fs.writeFileSync("index.html", index_html_output)