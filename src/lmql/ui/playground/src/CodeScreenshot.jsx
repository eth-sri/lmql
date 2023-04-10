import React, { useEffect, useState, useRef } from "react";
import styled from "styled-components";
// import monaco
import monaco from "@monaco-editor/loader";
import {registerLmqlLanguage} from "./editor/lmql-monaco-language";

const CodeScreenshotDiv = styled.div`
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    /* background-color: white; */
    z-index: 99999;
    display: flex;
    align-items: flex-start;
    justify-content: center;

    /* nice white, blue, red gradient */
    background: linear-gradient(90deg, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 33%, rgba(255,255,255,1) 66%, rgba(255,255,255,1) 100%);


    >.content {
        position: relative;
        transform-origin: top center;
    }

    .configuration {
        text-align: right;
        font-size: 10pt;
        position: absolute;
        top: 5pt;
        right: 5pt;
        background-color: white;
        color: grey;
        border-radius: 4pt;
        border: none;
        opacity: 0.0;

        :hover {
            opacity: 1.0;
        }
    }

    .lmql-spinner {
        font-size: 24pt;
        font-weight: bold;
        line-height: 1.5;
        background-color: #353535 !important;
        border: 0.5pt solid #212B3B;
        width: 25pt;
        position: absolute;
        height: 16pt;
        max-height: 24pt;
        border-radius: 2pt;
        opacity: 1.0;
        display: block;
        padding: 0;
        flex: 0;
        position: relative;
        left: 50%;
        transform: translateX(-50%) scale(0.7);
        margin-bottom: 10pt;
    }

    /* both parts pulse with an amplitude offset */
    .lmql-spinner .pt1 {
        color: white;
        animation: pulse 2s infinite;
        position: absolute;
        top: -6pt;
        left: 2pt;
    }

    .lmql-spinner .pt2 {
        color: white;
        font-size: 12pt;
        position: absolute;
        top: -2.5pt;
        right: 2pt;
        animation: pulse 2s infinite;
        animation-delay: 1s;
    }

    .lmql-spinner .pt3 {
        position: absolute;
        bottom: -5pt;
        right: -0.47pt;
        border: 5pt solid #353535;
        border-top-color: transparent;
        border-left-color: transparent;
        border-bottom-color: transparent;
    }

    /* the animation */
    @keyframes pulse {
        0% {
            opacity: 0.1;
        }

        50% {
            opacity: 0.8;
        }

        100% {
            opacity: 0.1;
        }
    }

    >* {
        font-family: sans-serif;
        line-height: 1.5;
        color: rgb(41, 41, 41);
        margin: 0;
        padding: 20pt;
    }

    h2 {
        display: none;
        position: fixed;
        top: -10pt;
        font-size: 40pt;
        left: 0pt;
        width: 100%;
        text-align: center;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        font-weight: 1200;
        color: #39414d;
    }

    h2 img {
        height: 0.9em;
        vertical-align: middle;
        position: relative;
        bottom: 4pt;
        margin-left: 4pt;
    }

    h1.url {
        font-size: 15pt;
        position: fixed;
        bottom: -20pt;
        right: 20pt;
        color: rgb(104, 103, 114);
        margin: 0;
        width: 100%;
        text-align: right;
        padding: 0;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        font-weight: 600;
    }

    h1.url .blue {
        color: rgb(92, 105, 250);
        /* color: white; */
    }


    .val0 { background-color: #6b77ff !important; }
    .val8 { background-color: #bc67ed !important; }
    .val7 { background-color: #f055cf !important; }
    .val2 { background-color: #ff4baa !important; }
    .val6 { background-color: #ff5482 !important; }
    .val3 { background-color: #ff6c5b !important; }
    .val5 { background-color: #ff8935 !important; }
    .val4 { background-color: #ffa600 !important; }
    .val1 { background-color: #f5d77e !important; }

    .loading-indicator {
        position: absolute;
        top: 50%;
        transform: scale(1.5);
        left: 0;
        right: 0;
        opacity: 0.5;
        animation: fadeout 0.5s ease-in-out forwards;
        animation-delay: 0.8s;
    }

    @keyframes fadeout {
        from {
            opacity: 0.5;
        }

        to {
            opacity: 0.0;
        }
    }

    .output {
        box-shadow: 0 0 100pt rgba(0, 0, 0, 0.0);
        border-radius: 4pt;
        width: 500pt;
        height: auto;
        margin-top: 10pt;
        padding: 10pt;
        border: 2pt solid rgb(210, 205, 205);
        font-size: 20pt;
        background-color: white;

        padding-top: 30pt !important;
        position: relative;

        color: transparent;
        /* animation: fadein 0.5s ease-in-out forwards; */
        /* animation-delay: 1.0s; */
    }

    @keyframes fadein {
        from {
            color: transparent;
        }

        to {
            color: black;
        }
    }

    .output::before {
        content: "Model Output";
        position: absolute;
        top: 5pt;
        left: 0;
        width: 100%;
        text-align: center;
        text-transform: uppercase;
        color: black;
        z-index: 999;
        font-size: 12pt;
        color: grey;
        font-weight: 300;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif
    }

    .columns.horizontal {
        flex-direction: row;
        align-items: flex-start;

        .column:first-child {
            margin-right: 10pt;
        }
    }

    .columns {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: flex-start;

        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        line-height: 1.5;
        position: relative;
        transform-origin: top center;
    }

    .columns .column {
        flex: 1;
        padding: 10pt;
    }

    .column.output {
        color: rgb(39, 39, 39);
        font-size: 15pt;
        margin-left: 0;

        white-space: pre-wrap;
        padding-bottom: -20pt;
    }

    .column.code label,
    .column.code .dot {
        display: none;
    }

    .column.code h3 {
        color: rgb(213, 212, 212);
    }

    .column.code h3 a {
        position: absolute;
        top: 8pt;
        font-size: 8pt;
        text-transform: none;
        right: 9pt;

        color: rgb(125, 120, 120);
    }

    .column.code h3 a:hover {
        color: rgb(201, 201, 201);
        text-decoration: underline;
    }

    .column.code {
        background-color: #24272D;
        border: 0.5pt solid grey;
        /* break lines on overflow */
        position: relative;
    }

    .column.code .title {
        position: absolute;
        top: 5pt;
        left: 0;
        width: 100%;
        text-align: center;
        text-transform: uppercase;
        color: black;
        z-index: 999;

        color: grey;
        font-weight: 300;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif
    }

    .column.code:before {
        content: "Model Output";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        text-align: center;
        z-index: -1;
        border-radius: 4pt;
        box-shadow: 0pt 0pt 20pt 0pt rgba(0, 0, 0, 0.5);
        font-size: 20pt;
    }

    .column.code pre {
        margin-top: 20pt;
    }

    .column.code pre a {
        color: #7d7a7a;
    }

    .column.code pre label a {
        color: #6e5ac7;
    }

    .column.code pre a:hover {
        text-decoration: underline;
    }

    .column.code {
        background-color: #24272D;

        /* box-shadow: 0 0 20pt rgba(0, 0, 0, 0.1); */
        border-radius: 5pt;
        width: 500pt;
        margin-top: 10pt;
        padding: 10pt;
        border: 2pt solid rgb(95, 95, 95);
        font-size: 12pt;
        color: white;
    }

    .output .variable.prompt {
        background-color: transparent;
    }

    .output .variable {
        border-radius: 0.2em;
        display: inline;
        background: #ccc;
        -webkit-box-decoration-break: clone;
        -ms-box-decoration-break: clone;
        -o-box-decoration-break: clone;
        box-decoration-break: clone;
        position: relative;

        padding: 0.1em;
        padding-right: 0.4em;
        margin-left: 0.1em;
    }

    .lmql-kw {
        font-weight: bold;
        color: #c678dd;
    }

    .lmql-str {
        color: #a7d884;
    }

    .lmql-comment {
        color: #5c6370;
    }


    .output .variable .variable-name {
        font-weight: 700;
        color: #333;
        background-color: rgba(0, 0, 0, 0.4);
        border-radius: 0.2em;
        font-family: monospace;
        color: rgba(255, 255, 255, 0.9);
        display: inline;
        margin: 0;
        margin-right: 0.6em;
        margin-left: 0;
        font-size: 0.7em;
        padding: 0.12em;
        position: relative;
        top: -0.2em;
        left: 0.1em;

        opacity: 0.0;
        animation: varNameFadeIn 0.15s;

        transform-origin: 0 50%;
        overflow: hidden;
    }

    @keyframes varNameFadeIn {
        0% {
            opacity: 0.0;
            max-width: 0pt;
        }

        100% {
            opacity: 1.0;
            max-width: 100%;
        }
    }

    .output .variable .variable-name.visible {
        opacity: 1.0;
    }

    .output .cursor {
        display: inline-block;
        width: 0.5em;
        height: 1.0em;
        background-color: white;
        opacity: 0.3;
        position: relative;
        top: 0.47em;
        left: 0.1em;
        border-radius: 0.1em;
        animation: blink 0.6s infinite;
        transform: scale(1.27) translateY(-0.25em);
        transition: all 1.2s;
    }

    .output .cursor:before {
        position: absolute;
        content: "";
        width: 100%;
        height: 100%;
        border-radius: 0.1em;
        background-color: rgba(0, 0, 0, 0.2);
    }

    body {
        height: 100vh;
        background: linear-gradient(90deg, #fffefe, #fef4f3);
    }

    .slider-thumb::before {
        position: absolute;
        content: "";
        left: 30%;
        top: 20%;
        width: 450px;
        height: 450px;
        background: #ffffff;
        border-radius: 62% 47% 82% 35% / 45% 45% 80% 66%;
        will-change: border-radius, transform, opacity;
        animation: sliderShape 5s linear infinite;
        display: block;
        z-index: -1;
        -webkit-animation: sliderShape 5s linear infinite;
        /* blure filter */
        filter: blur(200px);
    }

    @keyframes sliderShape {

        0%,
        100% {
            border-radius: 42% 58% 70% 30% / 45% 45% 55% 55%;
            transform: translate3d(0, 0, 0) rotateZ(0.01deg);
        }

        34% {
            border-radius: 70% 30% 46% 54% / 30% 29% 71% 70%;
            transform: translate3d(0, 5px, 0) rotateZ(0.01deg);
        }

        50% {
            transform: translate3d(0, 0, 0) rotateZ(0.01deg);
        }

        67% {
            border-radius: 100% 60% 60% 100% / 100% 100% 60% 60%;
            transform: translate3d(0, -3px, 0) rotateZ(0.01deg);
        }
    }

    @keyframes blink {
        0% {
            opacity: 0.3;
        }

        50% {
            opacity: 0.85;
        }

        100% {
            opacity: 0.3;
        }
    }

    /* .output {
        transition:  1.0s;
    } */

    .output.typing {
        border: 2pt solid rgb(167, 167, 246);
    }

    .output:not(.typing) {
        border: 2pt solid rgb(234, 233, 233);
    }

    .output.typing .cursor:first-child {
        left: 0pt;
    }

    .output:not(.typing) .cursor {
        opacity: 0.0 !important;
        animation: none !important;
    }
`

function setText(element, text) {
    let textBefore = element.text || "";
    if (text.startsWith(textBefore)) {
        element.text = text;
        return;
    }
    
    let commonIndex = 0;
    for (let i=0; i<Math.min(textBefore.length, text.length); i++) {
        if (textBefore[i] != text[i]) {
            break;
        }
        commonIndex = i;
    }
    element.text = text;
    element.offset = commonIndex;
}

function getCursorState(text, offset) {
    let context = "prompt"
    let varname = null;
    // determine context
    for (let i=offset; i>=0; i--) {
        if (text.substring(i).startsWith("<var ")) {
            context = "variable";
            varname = text.substring(i).split(" ")[1].split("=\"")[1].split("\"")[0].replace(/"/g, "");
            break;
        } else if (text.substring(i).startsWith("<prompt/>")) {
            context = "prompt";
            break;
        }
    }

    let next_offset = 1;

    text = text.substring(offset);

    if (text.startsWith("<prompt/>")) {
        context = "prompt";
        text = text.substring(9);
        next_offset = next_offset + 9;
    } else if (text.startsWith("<var ")) {
        context = "variable";
        varname = text.split(" ")[1].split("=\"")[1].split("\"")[0].replace(/"/g, "");
        let continuation_index = text.indexOf(">") + 1
        text = text.substring(continuation_index);
        next_offset = next_offset + continuation_index;
    }

    return {
        context: context,
        variable: varname,
        text: text,
        next_offset: next_offset
    }
}

function typeIn(element) {
    let content = element.innerText;

    element.innerHTML = `<span class='content'></span><span class='cursor'></span>
    </div>
    `;
    let containerElement = element;
    element = element.children[0];

    let chunkSize = 1;
    let currentVariable = null;
    let insertionPoint = element;
    let varCounter = varOffset;
    let interval = null;

    let varMapping = {}

    const advance = () => {
        let text = element.parentElement ? (element.parentElement.text || "") : "";
        let offset = element.parentElement ? (element.parentElement.offset || 0) : 0;
        let upper = chunkSize;
        let is_prompt = false;
        
        let i = 0;
        while (i<upper || is_prompt) {
            let cursor = getCursorState(text, offset + i);

            if (is_prompt && cursor.context != "prompt") {
                break
            }
            is_prompt = cursor.context == "prompt";
            // containerElement.classList.remove("typing");
            // nextElement

            if (cursor.variable === "eos") {
                containerElement.classList.remove("typing");
                // insert last line break
                insertionPoint.innerHTML += "<br>";
                clearInterval(interval);
                return;
            }

            if (cursor.context == "variable" && cursor.variable !== currentVariable) {
                currentVariable = cursor.variable;
                const varSpan = document.createElement("span");
                varSpan.classList.add("variable");
                if (varMapping[currentVariable]) {
                    varSpan.classList.add("val" + varMapping[currentVariable]);
                } else {
                    varMapping[currentVariable] = varCounter;
                    varSpan.classList.add("val" + varCounter);
                    varCounter = (varCounter + 1) % 9;
                }

                varSpan.setAttribute("data-name", currentVariable);
                element.appendChild(varSpan);
                // cursor.classList.add("var" + varCounter);
                insertionPoint = element.children[element.children.length - 1];

                const varNameSpan = document.createElement("span");
                varNameSpan.classList.add("variable-name");
                varNameSpan.innerHTML = currentVariable;
                insertionPoint.appendChild(varNameSpan);
                insertionPoint.children[insertionPoint.children.length - 1].classList.add("visible");
            } else if (cursor.context == "prompt" && currentVariable !== "prompt") {
                currentVariable = "prompt"
                const varSpan = document.createElement("span");
                varSpan.classList.add("prompt");
                element.appendChild(varSpan);
                insertionPoint = element.children[element.children.length - 1];
            } else if (cursor.context == "variable" && cursor.variable === currentVariable) {
                insertionPoint = element.children[element.children.length - 1];
            }

            let nextChunk = cursor.text[0]
            if (!nextChunk) {
                // clearInterval(interval);
                if (element.parentElement) element.parentElement.offset = offset + i;
                return;
            }

            if (cursor.text.startsWith("<br>")) {
                nextChunk = "<br>"
                i += "<br>".length - 1;
            }
            if (cursor.text.startsWith("<br/>")) {
                nextChunk = "<br/>"
                i += "<br/>".length - 1;
            }
            
            if (nextChunk === "<br>" || nextChunk === "<br/>") {
                nextChunk = document.createElement("br");
            } else {
                nextChunk = document.createTextNode(nextChunk);
            }
            insertionPoint.appendChild(nextChunk);

            i += cursor.next_offset
        }
        element.parentElement.offset = offset + i;
    }
    setTimeout(advance, 1);

    setTimeout(() => {
        containerElement.classList.add("typing");
    }, 1500);

    setTimeout(() => {
        interval = setInterval(advance, 10)
    }, 1800)
    
    window.setTimeout(() => {
        if (content.trim() != "") {
            setText(element.parentElement, content);
        }
    }, 100);
}

let cutOffState = 0;
let varOffset = 0;

export function CodeScreenshot(props) {
    let maxLength = props.maxLength || 60;
    const [highlightedCode, setHighlightedCode] = useState("");
    const outputRef = useRef(null);
    const contentRef = useRef(null);
    const [scale, setScale] = useState(1);
    const [fontScale, setFontScale] = useState(18);
    const [layout, setLayout] = useState("vertical");
    
    const [cutOff, setCutOff] = useState(0);
    const [_varOffset, setVarOffset] = useState(0);

    // restore on first 
    useEffect(() => {
        // restore also
        const storedScale = localStorage.getItem("code-screenshot-scale");
        const storedFontScale = localStorage.getItem("code-screenshot-font-scale");
        const storedLayout = localStorage.getItem("code-screenshot-layout");

        if (storedScale) {
            let scale = parseFloat(storedScale);
            if (!isNaN(scale)) {
                setScale(scale);
            }
        }
        if (storedFontScale) {
            let fontScale = parseFloat(storedFontScale);
            if (!isNaN(fontScale)) {
                setFontScale(fontScale);
            }
        }
        if (storedLayout) {
            setLayout(storedLayout);
        }
    }, []);

    // store layout, scale, fontScale to localStorage
    useEffect(() => {
        localStorage.setItem("code-screenshot-scale", scale);
        localStorage.setItem("code-screenshot-layout", layout);
        localStorage.setItem("code-screenshot-font-scale", fontScale);
    }, [scale, fontScale, layout]);
    
    // scale effect
    useEffect(() => {
        if (contentRef.current) {
            contentRef.current.style.transform = `scale(${scale})`;
        }
    }, [scale]);

    // on Esc hide
    useEffect(() => {
        const keydown = (e) => {
            if (e.key === "Escape") {
                props.hide();
            }
            // on R key 
            if (e.key === "r") {
                startTyping();
            }
            // check shift
            if (e.key === "+") {
                setFontScale(s => s + 1);
            }
            if (e.key === "_") {
                setFontScale(s => s - 1);
            }
            // +/-
            // with alt it is finer 
            let scale = e.altKey ? 0.01 : 0.1;
            if (e.key === "=") {
                setScale(s => s + scale);
            }
            if (e.key === "-") {
                setScale(s => s - scale);
            }
        }
        window.addEventListener("keydown", keydown);
        return () => {
            window.removeEventListener("keydown", keydown);
        }
    }, []);
    // mouse wheel scale
    useEffect(() => {
        const wheel = (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                let scale = e.deltaY * 0.001;
                setScale(s => s + scale);
            }
        }
        window.addEventListener("wheel", wheel);
        return () => {
            window.removeEventListener("wheel", wheel);
        }
    }, []);

    // output = [
    //     {
    //         "context": "prompt",
    //         "text": "Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?\nAnswer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021\nA: Let's think step by step. \n"
    //     },
    //     {
    //         "context": "variable",
    //         "variable": "REASONING",
    //         "text": "Sept. 1st, 2021 was a week ago, so 10 days ago would be 8 days before that, which is August 23rd, 2021.\n\nTherefore, the answer is (A) 08/23/2021.\n"
    //     },
    //     {
    //         "context": "prompt",
    //         "text": "Therefore, among A through F, the answer is "
    //     },
    //     {
    //         "context": "variable",
    //         "variable": "RESULT",
    //         "text": " A "
    //     },
    //     {
    //         "context": "variable",
    //         "variable": "eos",
    //         "text": " "
    //     }
    // ]

    const startTyping = () => {
        let output = []
        if (props.model_result && props.model_result.length > 0) {
            if (props.model_result[0].tokens.length > 0) {
                let content = props.model_result[0].tokens[0].content;
                while (content.startsWith(" ") || content.startsWith("\n")) {
                    content = content.substring(1);
                }

                props.model_result[0].tokens[0].content = content;
            }
            
            let first = true;
            for (let t of props.model_result[0].tokens) {
                let content = t.content.replaceAll("\\n", "\n").replaceAll("\\t", "\t");

                // apply cutoff
                if (first) {
                    first = false;
                    if (cutOffState > 0) {
                        content = content.substring(cutOffState);
                        content = "..." + content;
                    }
                }

                if (t.variable === "__prompt__") {
                    output.push({
                        "context": "prompt",
                        "text": content
                    })
                } else if (t.variable === "<eos>") {
                    output.push({
                        "context": "variable",
                        "variable": "eos",
                        "text": ""
                    })
                } else {
                    output.push({
                        "context": "variable",
                        "variable": t.variable.split("[")[0],
                        "text": content
                    })
                }
            }
        }
        // setParsedOutput(output);

        outputRef.current.offset = undefined;
        outputRef.current.text = undefined;
        // remove all children
        outputRef.current.innerHTML = "";
        // setText(outputRef.current, "");

        let acc = ""
        for (let element of output) {
            let newText = element.text
            if (element.context == "prompt") {
                newText = "<prompt/>" + newText;
            } else if (element.context == "variable") {
                newText = "<var name=\"" + element.variable + "\"/>" + newText;
            }
            acc += newText;
        }
        typeIn(outputRef.current, acc, varOffset % 9);
        setText(outputRef.current, acc);
    };

    // on mount type output
    useEffect(() => {
        monaco.init().then((monaco) => {
            registerLmqlLanguage(monaco)

            import('./editor/theme.json').then(data => {
                monaco.editor.defineTheme('solarized-dark', data);
                monaco.editor.setTheme('solarized-dark');

                // let fittingCode = props.code;
                // code 
                let fittingCode = props.code
                // break lines (do not break words) with indent if longer than 80 chars
                let lines = fittingCode.split("\n");
                fittingCode = "";
                for (let line of lines) {
                    let words = line.split(" ");
                    let indent = line.match(/^\s*/)[0];
                    let currentLine = "";
                    for (let word of words) {
                        if (currentLine.length + word.length > maxLength) {
                            fittingCode += currentLine + "\\ \n";
                            currentLine = indent + " ➥ " + word + " ";
                        } else {
                            currentLine += word + " ";
                        }
                    }
                    fittingCode += currentLine + "\n";
                }

                monaco.editor.colorize(fittingCode, "lmql", {}).then((result) => {
                    // let highlightedHTML = result;
                    // replace all < if not <span
                    // let highlighted = result.replace(/<([^(/span)|(span)|(br)])/g, "&lt;$1");
                    // split into lines
                    // highlighted = highlighted.split("<br/>");

                    // let n = 0;
                    // let resultCode = "";
                    // let tag_count = 0;
                    // let text = ""
                    // for (let c of result) {
                    //     if (c == "<") {
                    //         tag_count++;
                    //     }
                    //     let in_tag = tag_count % 2 == 1
                    //     if (c == ">") {
                    //         tag_count--;
                    //     }
                    //     if (c == "\n") {
                    //         n = 0;
                    //         console.log("newline", n)
                    //     }
                    //     if (n > maxLength && !in_tag && c == " ") {
                    //         resultCode += "\n";
                    //         console.log("newline", n)
                    //         n = 0;
                    //     }
                    //     if (!in_tag) {
                    //         n += 1
                    //         text += c;
                    //     }

                    //     resultCode += c;
                    // }

                    // console.log(text)
                    // console.log(resultCode)


                    setHighlightedCode(result.replaceAll("\\ </span>", "</span>"));
                })
                })
        })
    }, [props.code]);

    useEffect(() => {
        if (outputRef.current) {
            startTyping();
        }
    }, [outputRef.current]);
    
    return <CodeScreenshotDiv>
        <div className="configuration">
            <button className="hide" onClick={() => props.hide()}>
                Close (Esc)
            </button><br/>
            <button className="replay" onClick={() => startTyping()}>
                Replay (R)
            </button><br/>
            {/* toggle layout */}
            <button className="toggle-layout" onClick={() => setLayout(layout == "horizontal" ? "vertical" : "horizontal")}>
                {layout == "horizontal" ? "Vertical" : "Horizontal"}
            </button><br/>
            Initial Prompt Cutoff:<br/>
            <input value={cutOff} onChange={(e) => {
                cutOffState = e.target.value == "" ? 0 : parseInt(e.target.value)
                setCutOff(e.target.value == "" ? 0 : parseInt(e.target.value))
            }}></input><br/>
            Variable Color Offset:<br/>
            <input value={_varOffset} onChange={(e) => {
                varOffset = e.target.value == "" ? 0 : parseInt(e.target.value)
                setVarOffset(e.target.value == "" ? 0 : parseInt(e.target.value))
            }}></input><br/>
            Font Size via Keys _ (down) and + (up)<br/>
            Overall Scale via Keys - (down) and = (up)<br/>
        </div>
        <div className="content" ref={contentRef}>
            <div className={"columns" + (layout === "horizontal" ? " horizontal" : " vertical")}>
                <div className="column code" id="code">
                    <div className="title">LMQL</div>
                    <pre dangerouslySetInnerHTML={{
                        "__html": highlightedCode
                    }}></pre>
                </div>
                <div className="column output" id="output" ref={outputRef} style={{"fontSize":(fontScale) + "pt"}}></div>
                <div className="slider-thumb"></div>
            </div>
            <h1 className="url">
                <img src="https://lmql.ai/lmql.svg" alt="LMQL Logo" style={{height: "0.9em", verticalAlign: "middle", position: "relative", left: "-0.1em", top: "-0.1em"}}/>
                <span className="blue">lmql.ai</span>
            </h1>
        </div>
    </CodeScreenshotDiv>
}