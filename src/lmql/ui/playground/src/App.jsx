import './graph-layout.css';

import styled from 'styled-components';
import Editor from "@monaco-editor/react";
import React, { useEffect, useRef, useState } from "react";
import { registerLmqlLanguage } from "./editor/lmql-monaco-language";
import { BsSquare, BsFillExclamationSquareFill, BsBoxArrowUpRight, BsArrowRightCircle, BsFillCameraFill, BsCheckSquare, BsSendFill, 
  BsFileArrowDownFill, BsKeyFill, BsTerminal, BsFileCode, BsGithub, BsCardList, BsFullscreen, BsXCircle, BsFillChatLeftTextFill, 
  BsGear, BsGridFill, BsPlus, BsBook } from 'react-icons/bs';
import { DecoderGraph } from './DecoderGraph';
import { BUILD_INFO } from './build_info';
import exploreIcon from "./explore.svg"
import { ExploreState, Explore, PromptPopup, Dialog } from './Explore'
import { CodeScreenshot } from "./CodeScreenshot";
import { errorState, persistedState, trackingState, displayState} from "./State"
import { configuration, LMQLProcess, isLocalMode} from './Configuration';
import { ValidationGraph } from "./ValidationGraph";
import { DataListView } from "./DataListView";

import {reconstructTaggedModelResult} from "./tagged-model-result"

const ExploreIc = styled.img.attrs(props => ({ src: exploreIcon }))`
  width: 8pt;
  height: 8pt;
  position: relative;
  top: 0pt;
  right: 2pt;
`

const ResizeObservers = {
  addResizeListener: l => ResizeObservers.listeners.push(l),
  removeResizeListener: l => ResizeObservers.listeners = ResizeObservers.listeners.filter(x => x !== l),
  listeners: [],
  notify: () => ResizeObservers.listeners.forEach(l => l()),
}

const bg = '#252526';

const ContentContainer = styled.div`
  /* width: 900pt; */
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  
  color: white;
  flex: 1;
  position: fixed;
  top: 0;
  left: 0;
  width: calc(100% - 4pt);
  height: calc(100% - 2pt);
  margin: 2pt;
`;

const Panel = styled.div.attrs(props => ({ className: "panel" }))`
  /* min-height: 300pt; */
  background-color: ${bg};
  border-radius: 5pt;
  padding: 10px;
  display: flex;
  flex-direction: column;
  margin-left: 1.5pt;
  margin-right: 1.5pt;
  width: 40%;
  position: relative;

  // animate width and opacity change
  transition: width 0.1s, opacity 0.1s, padding 0.1s;
  overflow: hidden;

  /* light box shadow */
  box-shadow: 0 0 20px 0px #0000004f;

  // contained h2
  & > h2 {
    margin: 0;
    padding: 0;
    font-size: 10pt;
    font-weight: 400;
    color: #cccccc;
    margin-bottom: 5pt;
    display: flex;
    flex-direction: row;
  }

  // contained textarea
  & > textarea {
    width: 100%;
    height: 100%;
    background-color: ${bg};
    border: none;
    color: white;
    font-family: monospace;
    font-size: 14pt;
    outline: none;
    resize: none;

    // monospace font
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
    font-size: 14pt;
  }

  // when .sidebar
  &.with-sidebar {
    padding-right: 40pt;
  }

  // when .hidden
  &.hidden {
    width: 0pt;
    margin-left: 2pt;
    overflow: hidden;
    padding-left: 0;
    padding-right: 35pt
  }
  // when .stretch
  &.stretch {
    flex: 1;
    height: auto;
  }

  &.hidden .sidebar {
    border-left: none;
  }
`

const Title = styled.h1`
  font-size: 1.2em;
  margin-left: 5pt;
  margin-right: 15pt;
  text-align: left;
  font-weight: 400;
  font-family: 'Open Sans', sans-serif;
  color: ${bg};

  img {
    width: 12pt;
    height: 12pt;
    position: relative;
    margin-right: 9pt;
    margin-left: 5pt;
    top: 2pt;
  }

  span.badge {
    background-color: #383666;
    font-size: 8pt;
    padding: 2pt;
    border-radius: 2pt;
    color: white;
    margin-left: 5pt;
    position: relative;
    top: -1pt;
  }
`;

const Sidebar = styled.div.attrs(props => ({ className: "sidebar" }))`
  width: 35pt;
  border-radius: 5pt;
  border-top-left-radius: 0pt;
  border-bottom-left-radius: 0pt;
  background-color: ${bg};
  border-left: 1px solid #333;
  margin-left: 2pt;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 3pt;
  height: 100%;
`

const TokenCountDiv = styled.div`
  font-size: 6pt;
  color: #a19a9a;
  flex: 1;
  /* position: absolute; */
  /* bottom: 10pt; */
  text-align: right;
  right: 20pt;
  z-index: -1;
  padding: 5pt;
  white-space: pre-line;
  max-height: 10pt;

  /* indicate copy */
  cursor: pointer;
`

function TokenCountIndicator() {
  const [stats, setStats] = useState({})

  const format_cost = (c, precision) => {
    if (c == 0) {
      return "$0.00"
    }
    c = c.toFixed(precision)
    if (c === (0).toFixed(precision))
      return "<$" + (Math.pow(10, -precision)).toFixed(precision);
    return "$" + c;
  }

  const cost_estimate = (model, k_tokens, precision = 2) => {
    if (model.includes("text-davinci")) {
      return `${format_cost(k_tokens * 0.02, precision)}`
    } else if (model.includes("text-ada")) {
      return `${format_cost(k_tokens * 0.0004, precision)}`
    } else if (model.includes("text-babbage")) {
      return `${format_cost(k_tokens * 0.0005, precision)}`
    } else if (model.includes("text-curie")) {
      return `${format_cost(k_tokens * 0.002, precision)}`
    } else if (model.includes("turbo")) {
      return `${format_cost(k_tokens * 0.002, precision)}`
    } else if (model.includes("gpt-4")) {
      // todo this is an estimate, as prompt tokens count less
      return `${format_cost(k_tokens * 0.06, precision)}`
    } else {
      return ""
    }
  }

  useEffect(() => {
    let interval = window.setInterval(() => {
      setStats(s => {
        if (s == null || Object.keys(s).length === 0) {
          return {}
        } else {
          return {
            ...s,
            _now: Date.now()
          }
        }
      })
    }, 1000)
    return () => {
      window.clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    const onStatus = s => {
      if (s.status === "idle") {
        setStats(s => ({ ...s, _end: Date.now() }))
      }
    }
    LMQLProcess.on("status", onStatus)
    
    const renderer = {
      add_result: (data) => {
        if (data.type == "openai-token-count") {
          setStats(s => {
            if (s == null || Object.keys(s).length == 0) {
              return {
                ...data.data,
                _start: Date.now()
              }
            } else {
              return {
                ...s,
                ...data.data,
              }
            }
          })
        }
      },
      clear_results: () => setStats({})
    };
    LMQLProcess.on("render", renderer)
    return () => {
      LMQLProcess.remove("render", renderer)
      LMQLProcess.remove("status", onStatus)
    }
  }, [])

  let text = ""
  let tokenCount = 0;
  let model = ""
  let steps = 1;
  let copyString = ""
  if (stats.tokens || stats._step) {
    tokenCount = stats.tokens
    model = stats.model
    steps = stats._step || 1
    // first upper 
    const otherKeys = Object.keys(stats)
      .filter(k => k != "tokens")
      .filter(k => !k.startsWith("_"))
      .filter(k => k != "model")
    const toFirstUpper = k => k.charAt(0).toUpperCase() + k.slice(1)
    text = `Tokens: ${tokenCount}, ${otherKeys.map(k => `${toFirstUpper(k)}: ${stats[k]}`).join(", ")}`

    copyString = `Tokens: ${tokenCount}\n${otherKeys.map(k => `${toFirstUpper(k)}: ${stats[k]}`).join("\n")}`

    // time elapsed
    if (stats._start) {
      const end = stats._end || stats._now || Date.now();
      const elapsed = (end - stats._start) / 1000
      text += `\n Time: ${elapsed.toFixed(1)}s, `
      copyString += `\nTime: ${elapsed.toFixed(1)}s, `
    }

    text += `${(tokenCount / steps).toFixed(2)} tok/step`
    if (model.includes("openai")) {
      text += ` Est. Cost ${cost_estimate(model, tokenCount / 1000, 4)}`
      copyString += `\nEst. Cost ${cost_estimate(model, tokenCount / 1000, 4)}`
    }
  }

  return <TokenCountDiv onClick={() => {
    navigator.clipboard.writeText(copyString)
  }}>
    {text}
  </TokenCountDiv>
}

// const PlotContainer = styled.div`
//   flex: 1;
//   padding: 10pt;
//   position: relative;
//   display: flex;
//   flex-direction: column;
//   align-items: stretch;
//   justify-content: stretch;

//   svg.main-svg {
//     border-radius: 5pt;
//     overflow: hidden;
//   }
// `


// function StatisticsPanelContent(props) {
//   const [stats, setStats] = useState([])

//   const format_cost = (c, precision) => {
//     c = c.toFixed(precision)
//     if (c == (0).toFixed(precision)) 
//       return "<$" + (Math.pow(10, -precision)).toFixed(precision);
//     return "$" + c;
//   }

//   const cost_estimate = (model, k_tokens, precision=2) => {
//     if (model.startsWith("text-davinci")) {
//       return `, Cost: ${format_cost(k_tokens * 0.02, precision)}`
//     } else if (model.startsWith("text-ada")) {
//       return `, Cost: ${format_cost(k_tokens * 0.0004, precision)}`
//     } else if (model.startsWith("text-babbage")) {
//       return `, Cost: ${format_cost(k_tokens * 0.0005, precision)}`
//     } else if (model.startsWith("text-curie")) {
//       return `, Cost: ${format_cost(k_tokens * 0.002, precision)}`
//     } else {
//       return ""
//     }
//   }

//   const extend_timeseries = (data) => {
//     const t = data._step
//     const newStats = stats.slice()
//     newStats.push(data)
//     setStats(newStats)
//   }

//   useEffect(() => {
//     LMQLProcess.on("render", {
//       add_result: (data) => {
//         if (data.type == "openai-token-count") {
//           extend_timeseries(data.data)
//         }
//       },
//       clear_results: () => setStats([])
//     })
//   })

//   if (stats.length > 0) {
//     const tokenCount = stats.map(s => s.tokens)
//     const model = stats[0].model
//     const otherKeys = Object.keys(stats[0]).filter(k => k != "tokens").filter(k => !k.startsWith("_"))
//     const otherData = otherKeys.map(k => {
//       return {
//         name: k,
//         data: stats.map(s => s[k])
//       }
//     })

//     let plots = [
//       {
//         x: Array.from(Array(tokenCount.length).keys()),
//         y: tokenCount,
//         type: 'scatter',
//         mode: 'lines+markers',
//         marker: {color: 'red'},
//       }
//     ]

//     return <PlotContainer style={props.style}>
//       <Plot 
//       data={plots} 
//       style={{flex: 1, padding: "10pt", borderRadius: "5pt"}}
//       className="plot"
//     />
//     </PlotContainer>
//   } else {
//     return <CenterBox style={props.style}><h2>No Statistics Available</h2></CenterBox>
//   }
// }

const ModelSelectionDiv = styled.div`
  flex: 1;
  position: absolute;
  background-color: transparent;
  margin: 2pt;
  text-align: right;
  top: 0pt;
  right: 0pt;
  height: 18pt;
  width: 40%;

  &:hover {
    border-bottom: 1pt solid grey;
  }

  &:active {
    text-decoration: underline;
  }

  &.auto {
    opacity: 0.2
  }

  &.auto:hover, &.auto:active {
    opacity: 1.0
  }

  >input {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border: none;
    outline: none;
    background-color: #ffffff19;
    background: none;
    text-align: right;
    z-index: 990;
    display: block;
  }

  .select {
    position: absolute;
    flex-direction: column;
    top: calc(100% + 5pt);
    bottom: auto;
    width: 100%;
    color: black;
    background-color: white;
    border-radius: 4pt;
    text-align: left;
    max-height: 300pt;
    max-height: calc(100vh - 100pt);
    overflow-y: scroll;
    display: none;
    z-index: 999;
    padding-bottom: 10pt;
  }

  .select.open {
    display: flex;
  }

  .select .option:hover {
    background-color: #f0f0f0aa;
    cursor: pointer;
  }

  .select .option:first-child {
    border-top: none;
  }

  .select .option {
    text-align: left;
    padding: 4pt;
    font-family: monospace;
    margin: 0pt 0pt;
    border-radius: 2pt;
    border-top: 0.5pt solid #d6d6d6;
    font-size: 8pt;
    display: flex;
    flex-direction: row;
  }

  .option .note {
    text-align: right;
    display: block;
    flex: 1;
    font-size: 6pt;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    line-height: 10pt;
  }

  .select h2 {
    font-size: 8pt;
    margin: 8pt 4pt;
    font-weight: normal;
    padding: 0;
  }

  .select .instructions {
    display: block;
    font-size: 8pt;
    padding: 5pt;
    color: #3c3c3c;
  }

  .option:hover.selected, .option.selected {
    background-color: #c4c4c4;
  }
  
  >input {
    z-index: 3;
    right: 20pt;
    font-size: 8pt;
    color: #ffffffae;
    padding-left: 5pt;
    font-family: monospace;
    z-index: 999;
    border-radius: 2pt;
  }

  &.active input, input:focus {
    background-color: #ffffff3c !important;
  }

  .select h2:first-of-type {
    font-weight: bold !important;
  }

  svg {
    position: absolute;
    top: 3.5pt;
    height: 10pt;
    width: 10pt;
    right: 7pt;
    z-index: 1;
    opacity: 0.4;
  }

  .overlay {
    background-color: black;
    width: 100vw;
    height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    opacity: 0.3;
    z-index: 20;
  }
`

function ModelSelection() {
  const [model, setModel] = useState(persistedState.getItem("playground-model"))
  const [selectOpen, setSelectOpen] = useState(false)

  const onChange = (value) => {
    persistedState.setItem("playground-model", value)
    setModel(value)
  }

  const PREDEFINED = {
    "": [
      {"name": "automatic", note: "Use model as specified by the query.", inprocess: false},
      {"name": "random", note: "Random (uniform) token sampling.", inprocess: false}
    ],
    "Other Suggestions": [
      {"name": "openai/text-ada-001", "note": "OpenAI", inprocess: false},
      {"name": "openai/text-curie-001", "note": "OpenAI", inprocess: false},
      {"name": "openai/text-babbage-001", "note": "OpenAI", inprocess: false},
      {"name": "openai/text-davinci-001", "note": "OpenAI", inprocess: false},
      {"name": "openai/text-davinci-003", "note": "OpenAI", inprocess: false},
      {"name": "chatgpt", "note": "OpenAI", inprocess: false},
      {"name": "gpt-4", "note": "OpenAI", inprocess: false}
    ]
  }

  if (!configuration.BROWSER_MODE) {
    PREDEFINED["Other Suggestions"] = Array.from([
      {"name": "gpt2", "note": "🤗 Tranformers", inprocess: true},
      {"name": "gpt2-medium", "note": "🤗 Tranformers", inprocess: true},
      {"name": "facebook/opt-350m", "note": "🤗 Tranformers", inprocess: true},
      {"name": "llama.cpp:<PATH>/llama-7b.bin", "note": "🦙 llama.cpp", inprocess: true},
    ]).concat(PREDEFINED["Other Suggestions"])
  }

  const onInputEnter = (e) => {
    if (e.key == "Enter") {
      setSelectOpen(false)
      e.target.blur()
    }
  }

  return <ModelSelectionDiv className={(model == "automatic" ? "auto" : "") + (selectOpen ? " active" : "") }>
    <input spellCheck={false} placeholder="automatic" value={model} onChange={e => onChange(e.target.value)} autoCorrect={false} onKeyDown={onInputEnter}/>
    <div className={'select ' + (selectOpen ? "open" : "")}>
      <span class="instructions">
        <b>Custom Model</b><br/>
        Specify the model to execute your query with. You can also type in the text field above.
        {configuration.BROWSER_MODE ? <><br/><a href={"https://docs.lmql.ai/en/latest/quickstart.html"} target="_blank" rel="noreferrer" className="hidden-on-small">
          Install LMQL locally </a> to use other models, e.g. from 🤗 Tranformers</>
        : null}
      </span>
      {Object.keys(PREDEFINED).map(k => <>
        {k != "" ? <h2 key={"key-"+k}>{k}</h2> : null}
        {PREDEFINED[k].map(o => <div className={'option' + (o.name == model ? " selected" : "")} 
          onClick={() => {onChange(o.name); setSelectOpen(false);}} key={k+o}>
          {o.name}
          <span class="note">
            {o.note}
          </span>
        </div>)}
        </>)
      }
    </div>
    <div class="overlay" style={{display: selectOpen ? "block" : "none"}} onClick={() => setSelectOpen(false)}></div>
    <BsPlus onClick={() => setSelectOpen(!selectOpen)}/>
  </ModelSelectionDiv>
}

const EditorContainer = styled.div`
  flex: 1;
  overflow: hidden;
  height: auto;
`

function EditorPanel(props) {
  const editorContainer = useRef(null);
  
  props = Object.assign({
    onRun: () => { },
  }, props);

  props.status = props.processState
  props.processState = props.status.status

  function handleEditorDidMount(editor, monaco) {
    ResizeObservers.addResizeListener(() => {
      let fontSize = window.innerWidth < 700 ? 12 : 16
      editor.updateOptions({ "fontSize": fontSize })
      window.setTimeout(() => {
        editor.layout()
      }, 100)
    })

    registerLmqlLanguage(monaco);
    import('./editor/theme.json')
      .then(data => {
        monaco.editor.defineTheme('solarized-dark', data);
        monaco.editor.setTheme('solarized-dark');
      })
    
    persistedState.on("lmql-editor-contents", (contents) => {
      if (editor.getValue() == contents) return;
      let fontSize = window.innerWidth < 700 ? 10 : 16
      editor.updateOptions({ "fontSize": fontSize })
      editor.setValue(contents)
    });
    
    editor.onDidChangeModelContent(() => {
      persistedState.setItem("lmql-editor-contents", editor.getValue())
    })
  }
  
  let fontSize = window.innerWidth < 700 ? 10 : 16
  if (displayState.mode == "embed") fontSize = 10

  return (
    <Panel className='stretch max-width-50' id='editor-panel' style={{
      display: "flex",
    }}>
      <h2>Program</h2>
      <EditorContainer ref={editorContainer}>
      <Editor
        defaultValue={persistedState.getItem("lmql-editor-contents") || ""}
        theme="vs-dark"
        // no minimap
        options={{
          // no minimap
          minimap: { enabled: false },
          // no line numbers
          lineNumbers: "off",
          // font size 14pt
          fontSize: fontSize,
          // line wrap
          wordWrap: "on",
          // tabs are spaces
          tabSize: 4,
          // show whitespace
          renderWhitespace: "all",
          // set font family
          fontFamily: "Fira Code, monospace",
          automaticLayout: true
        }}
        // custom language
        defaultLanguage="lmql"
        style={{ maxHeight: "80%" }}
        onMount={handleEditorDidMount}
      />
      </EditorContainer>
      <ButtonGroup>
        <FancyButton className='green' onClick={() => props.onRun()} disabled={props.processState != "idle" && props.processState != "secret-missing"}>
          {props.processState == "running" ? <>Running...</> : <>&#x25B6; Run</>}
        </FancyButton>
        {/* status light for connection status */}
        <StatusLight connectionState={props.status} />
        <StopButton onClick={() => {
          LMQLProcess.kill()
        }} disabled={props.processState != "running"}>
          {/* utf8 stop square */}
          <i>&#x25A0;</i> Stop
        </StopButton>
        <ErrorIndicator/>
        {/* <Spacer></Spacer> */}
        <TokenCountIndicator />
      </ButtonGroup>
      <ModelSelection/>
    </Panel>
  );
}

const ButtonErrorIndicator = styled.button`
  background: none;
  border: none;
  color: #dda7a7;
  font-weight: bold;
  border-radius: 5pt;
  font-size: 8pt;
  display: inline-block;
  padding: 4pt;

  :hover {
    text-decoration: underline;
    cursor: pointer;
  }

  svg {
    margin-right: 4pt;
    position: relative;
    top: 1pt;
    color: #a23a3a;
  }
`

function ErrorIndicator() {
  const [hasError, _setHasError] = useState(false);
  // connect hasError to global errorState
  useEffect(() => {
    const l = s => _setHasError(s)
    errorState.addListener(l)
    return () => errorState.removeListener(l)
  }, [])

  const onClick = () => {
    errorState.setError(false);
    errorState.showErrorOutput()
  }

  if (!hasError) return null;

  return <ButtonErrorIndicator onClick={onClick}>
    <BsFillExclamationSquareFill/>
    Check Output
  </ButtonErrorIndicator>
}

const Row = styled.div`
  display: flex;
  align-items: stretch;
  flex-direction: row;
  margin-bottom: 3pt;
  height: calc(50% - 20pt - 4pt);

  &.simple-mode.simple {
    flex: 1;
    height: calc(100% - 40pt);
  }

  &.simple-mode:not(.simple) {
    height: 0pt;
    border: 1pt solid red;
    display: none;
  }

  /* if screen < 320pt */
  @media (max-width: 40em) {
    &.simple-mode {
      flex-direction: column;
      height: calc(100%);
      padding: 0;
      margin-right: 4pt;
    }

    &.simple-mode.simple .panel {
      flex: 1;
      margin: 0;
      margin-top: 1pt;
      width: calc(100% - 10pt);
      border-radius: 0;
      font-size: 0.8em;
      /* special case for with-sidebar */
      &.with-sidebar {
        width: calc(100% - 15pt - 27.5pt);
      }
    }
  }
`

const IconButton = styled.button`
  background-color: transparent;
  border: none;
  outline: none;
  cursor: pointer;
  color: white;
  font-size: 0.8em;
  width: 28pt;
  height: 28pt;
  margin-top: 4pt;
  
  // hover highlight
  &:hover {
    background-color: #333;
  }

  /* checked state */
  &.checked {
    /* slightly darker thana bove */
    background-color: #444;
  }
  
  // click highlight
  &:active {
    background-color: #444;
  }

  // active
  &.active {
    background-color: #444;
  }

  border-radius: 5pt;
`

const ToolbarIconButton = styled(IconButton)`
  padding: 0;
  padding-left: 4pt;
  padding-right: 4pt;
  margin-left: 5pt;
  border-radius: 2pt;
  width: auto;
  height: 14pt;

  > span {
    margin-left: 4pt;
  }

  &.checked > span, &.checkable > span {
    margin-left: 0pt;
  }

  > svg {
    position: relative;
    top: 0.5pt;
  }
`

function CheckableToolbarIconButton(props) {
  let p = Object.assign({
    checked: false,
    onClick: () => { },
  }, props);
  return <ToolbarIconButton className={p.checked ? "checked checkable" : "checkable"} onClick={p.onClick}>
    {p.checked ? <BsCheckSquare size={8} /> : <BsSquare size={8} />}
    <span className="spacer wide"> </span>
    {p.children}
  </ToolbarIconButton>
}

function OutputPanelContent(props) {
  const [output, setOutput] = useState("Client ready.\n");
  const [alwaysShow, setAlwaysShow] = useState(false);

  const onConsoleOut = data => {
    let newOutput = ""
    if (typeof data === 'string') {
      newOutput = data
    } else {
      newOutput = JSON.stringify(data, null, 2);
    }
    /* console.lo(newOutput) */
    if (newOutput.toLowerCase().includes("error") || newOutput.toLowerCase().includes("exception")) {
      errorState.setError(true)
    }
    setOutput(s => s + newOutput);
  };

  // on mount
  useEffect(() => LMQLProcess.addConsoleListener(onConsoleOut))

  // on unmount
  useEffect(() => () => LMQLProcess.remove("console", onConsoleOut))

  props.clearTrigger.addTriggerListener(() => {
    setOutput("");
    errorState.setError(false);
  })

  props = Object.assign({}, props)
  props.style = Object.assign({
    fontSize: "8pt",
  }, props.style)

  return <>
    {props.className == "simple" &&
    <ToggleButton checked={alwaysShow} onClick={() => setAlwaysShow(s => !s)} style={{ float: "right", color: "white" }}>...</ToggleButton>}
    <OutputText style={props.style} className={props.className + (alwaysShow ? " always" : "")} readOnly={true} value={output}></OutputText>
  </>
}

const ModelResultText = styled.div`
  flex: 1; 
  display: flex;
  flex-direction: column;
  line-height: 1.6em;
  white-space: pre-wrap;
  overflow-y: auto;
  font-size: 10pt;

  &::-webkit-scrollbar {
    width: 0px;
  }

  h3 {
    margin: 0;
    padding: 0;
    font-size: 12pt;
  }

  &:active div {
    background-color: rgba(255, 255, 255, 0.01);
  }

  span {
    padding: 1pt;
  }

  div {
    padding: 5pt;
    background-color: rgba(255, 255, 255, 0.02);
    border-radius: 2pt;
    flex:1;
    padding-bottom: 20pt;
  }

  div .prompt {
    opacity: 0.95;
  }
  
  &.chat-mode {
    padding-bottom: 50pt;
  }

  &.chat-mode .system-message {
    display: block;
    font-size: 8pt;
  }

  .system-message {
    display: none;
    text-align: center;
  }

  div .tag {
    display: block;
    text-align: center;
    font-size: 8pt;
    color: #5c5c5c;
    display: none;
  }

  &.chat-mode .variable.eos {
    display: inline;
    opacity: 0.5;
    text-align: center;
  }

  div .tag-system:after {
    content: "System";
    position: absolute;
    right: 5pt;
    top: 0pt;
    font-size: 8pt;
    text-transform: uppercase;
  }

  div .tag-system {
    display: block;
    text-align: center;
    background-color: #ffffff13;
    border-radius: 2pt;
    font-size: 90%;
    margin-top: 10pt;
    margin-bottom: 10pt;
    color: #c0c0c0;
  }

  div .tag-assistant {
    /* display: inline-block; */
    /* border: 1pt solid #5c5c5c; */
    /* margin-top: 5pt;
    margin-right: 4%; */

    /* border-radius: 8pt; */
    overflow: hidden;
    /* padding: 4pt; */
  }

  div .tag-user {
    display: block;
    margin-left: 10%;
    position: relative;
    border: 1pt solid #5c5c5c;
    border-radius: 8pt;
    padding: 4pt;
    margin-bottom: 10pt;
    margin-top: 5pt;
  }
  
  &>div>span:first-child {
    margin-left: 0pt;
    padding-left: 0pt;
  }

  span.escape {
    color: #5c5c5c;
  }

  div .variable {
    color: white;
    background-color: #333;
    opacity: 1.0;
    border-radius: 2pt;
    margin-left: 2pt;
  }

  div .badge {
    padding: 1.0pt 4pt;
    border-radius: 2pt;
    font-size: 0.9em;
    background-color: rgba(0, 0, 0, 0.5);
    position:relative; 
    top: -0.05em;
    margin-right: 2pt;
    user-select: none;
    /* exclude from text selection */
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
  }

  div .badge:last-child {
    margin-right: 0;
  }

  div .variable.v0 { background-color: #6b77ff; }
  div .variable.v8 { background-color: #bc67ed; }
  div .variable.v7 { background-color: #f055cf; }
  div .variable.v2 { background-color: #ff4baa; }
  div .variable.v6 { background-color: #ff5482; }
  div .variable.v3 { background-color: #ff6c5b; }
  div .variable.v5 { background-color: #ff8935; }
  div .variable.v4 { background-color: #ffa600; }
  div .variable.v1 { background-color: #dca709; }

  .chat-input {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 35pt;
    background-color: ${bg} !important;
    border-top: 1pt solid #5c5c5c;
    box-shadow: 0pt 0pt 10pt 0pt rgba(0, 0, 0, 0.5);
    padding: 5pt;
    /* padding-top: 18pt; */
    padding-right: 7.5pt;
    display: flex;
  }

  .chat-input h3 {
    position: absolute;
    top: 0;
    left: 8pt; 
    font-size: 8pt;
    text-transform: uppercase;
    margin: 0;
    padding: 0;
    margin-right: 10pt;
    color: rgb(184, 179, 179);
  }

  .chat-input button {
    margin-left: 5pt;
  }

  .chat-input textarea {
    display: block;
    border-radius: 2pt;
    flex: 1;
    max-height: 100pt;
    min-height: 20pt;
    font-size: 12pt;
    border-radius: 4pt;
    /* outline radius */
    outline: 0pt solid transparent;
    border: 1pt solid transparent;
    background-color: rgba(255, 255, 255, 0.1);
    
    &:focus {
      border: 1pt solid #6b77ff;
      box-shadow: 0pt 0pt 10pt 0pt rgba(112, 126, 250, 0.095);
      /* radius of outline */
    }
  }

  .chat-input.disabled {
    opacity: 0.2;
  }
`

const TypingIndicator = styled.span`
  display: inline-block;
  width: 8pt;
  height: 12pt;
  position: relative;
  border-radius: 2pt;
  top: 3.5pt;
  left: 2pt;
  background-color: #d7d5d5;
  animation: typing 1s infinite;

  @keyframes typing {
    0% { opacity: 0.2; }
    50% { opacity: 1; }
    100% { opacity: 0.2; }
  }
`

class Truncated extends React.Component {
  constructor(props) {
    super(props)
    
    this.state = {
      typingOffset: 1024,
      expandedText: ""
    }
    this.stepper = null
  }

  componentDidMount() {
    this.stepper = setInterval(() => {
      this.setState(s => Object.assign(s, { typingOffset: s.typingOffset + 16 }))
    }, 5)
  }

  componentWillUnmount() {
    clearInterval(this.stepper)
  }

  componentDidUpdate(prevProps) {
    if (prevProps.tokens != this.props.tokens) {
      let tokens = this.props.tokens
      let prevTokens = prevProps.tokens

      if (!tokens || !prevTokens) {
        this.setState({ typingOffset: 0 })
        return;
      }

      let commonPrefixOffset = 0

      for (let i = 0; i < Math.min(prevTokens.length, tokens.length); i++) {
        let c = tokens[i]
        let cPrev = prevTokens[i]
        
        let content = c.content
        let prevContent = cPrev.content

        if (content != prevContent) {
          let j = 0
          while (j < Math.min(content.length, prevContent.length) && content[j] == prevContent[j]) {
            j++
          }
          commonPrefixOffset += j
          break;
        } else {
          if (c.variable != "__prompt__") {
            commonPrefixOffset += content.length
          }
        }
      }
      this.setState({ typingOffset: commonPrefixOffset })
    }
  }

  renderVariableName(variable) {
    if (variable.endsWith("[0]")) {
      return variable.substr(0, variable.length - 3)
    }
    return variable
  }

  renderContent(content) {
    // make sure to render model output control characters
    content = content.replace(/\\n/g, "\n")
    content = content.replace(/\\t/g, "\t")

    /* convert text to char code */
    let bytes = []
    for (let i = 0; i < content.length; i++) {
      /* check for \xXX and parse charcode from hex */
      if (content[i] == "\\") {
        if (content[i + 1] == "x") {
          let hex = content.substring(i + 2, i + 4)
          let charCode = parseInt(hex, 16)
          bytes.push(charCode)
          i += 3
          continue;
        }
      }
      bytes = bytes.concat(Array.from(new TextEncoder("utf-8").encode(content[i])))
    }
    content = new TextDecoder("utf-8").decode(new Uint8Array(bytes))

    let EXPLICIT_CHARS = {
      "\n": "⏎",
      "\t": "⇥",
    }

    let elements = []
    let text = ""
    let i = 0;
    for (let c of content) {
      if (EXPLICIT_CHARS[c]) {
        elements.push(<>{text}</>)
        elements.push(<span className="escape" key={"escape_" + i}>{EXPLICIT_CHARS[c]}</span>)
        text = c
      } else {
        text += c;
      }
      i++;
    }
    elements.push(<>{text}</>)
    return elements
  }

  render() {
    const tokens = this.props.tokens

    let elements = []
    let characterCount = 0

    const isIncludedIndex = (i) => i < tokens.length && (characterCount < this.state.typingOffset || !this.props.typing)

    for (let i = 0; isIncludedIndex(i); i++) {
      let c = tokens[i]
      let content = c.content
      
      if (c.variable != "__prompt__") {
        characterCount += content.length
      }
      if (characterCount > this.state.typingOffset && this.props.typing) {
        content = content.substr(0, this.state.typingOffset - (characterCount - content.length))
      }

      // let escapedContent = this.renderContent(content)
      
      let segmentContent = <>
        {c.variable != "__prompt__" && <span key={i + "_badge-" + this.renderVariableName(c.variable)} className="badge">{this.renderVariableName(c.variable)}</span>}
        {c.content.length > 0 && <span key={i + "_content-" + c.content} className="content">
          {this.leftTruncated(i + "_content", content, i==0)}
        </span>}
      </>

      elements.push(<span key={i + "_segment-" + c.content} className={(c.variable != "__prompt__" ? "variable " : "") + c.variableClassName}>
        {segmentContent}
        {!isIncludedIndex(i+1) && this.props.typing && this.props.processStatus == "running" && this.props.waitingForInput !== "waiting" && <TypingIndicator/>}
      </span>)
    }


    // if (this.props.typing && this.props.processStatus == "running") {
    //   // use unicode block letter
    //   console.log(elements)
    //   elements.push(<TypingIndicator/>)
    // }
    
    return <>{elements}</>
  }

  setExpandedText(text) {
    this.setState(s => ({
      expandedText: text
    }))
  }

  leftTruncated(key, content, truncate) {
    const length = 250

    if (!truncate) return this.renderContent(content)
    if (content.length < length) return this.renderContent(content)

    const text = content

    return <span key={key}>
      {this.state.expandedText == text && <>{this.renderContent(text)}</>}
      {this.state.expandedText != text && <>
        <ExpandButton className="clickable" onClick={() => this.setExpandedText(text)}>...</ExpandButton>
        {this.renderContent(text.substr(text.length - length))}
      </>}
    </span>
  }
}

const ExpandButton = styled.button`
  background-color: #675f5f;
  color: #d2c4c4;
  font-weight: bold;
  border: none;
  border-radius: 4pt;
  padding: 2pt;
  padding-left: 10pt;
  padding-right: 10pt;
  margin-right: 4pt;

  :hover {
    background-color: #9f9898;
    cursor: pointer;
  }
`

function ModelResultContent(props) {
  const scrollRef = useRef(null)
  let mostLikelyNode = props.mostLikelyNode ? props.mostLikelyNode.data("id") : null
  const [waitingForInput, setWaitingForInput] = useState("hidden")

  const hasAnyOutput = mostLikelyNode != null

  const setInputState = React.useCallback((waiting) => {
    setWaitingForInput("disabled")
  })

  // on changes to props.mostLikelyNode scroll down to end of scroll view
  useEffect(() => {
    if (props.trackMostLikly) {
      let scroll = scrollRef.current
      scroll.scrollTop = scroll.scrollHeight
    }
  }, [mostLikelyNode, props.trackMostLikly])

  // monitor if LMQLProcess asks for input
  useEffect(() => {
    const renderer = {
      add_result: (data) => {
        if (data.type == "stdin-request") {
          setWaitingForInput("waiting")
        }
      },
      clear_results: () => setWaitingForInput("hidden"),
    };

    LMQLProcess.on("render", renderer)
    return () => {
      LMQLProcess.remove("render", renderer)
    }
  }, [])

  // when props.processStatus changes from "running", clear waiting for input
  useEffect(() => {
    if (props.processStatus != "running") {
      setWaitingForInput("hidden")
    }
  }, [props.processStatus])

  let modelResult = null;
  if (props.trackMostLikly) {
    modelResult = reconstructTaggedModelResult([props.mostLikelyNode])
  } else {
    modelResult = reconstructTaggedModelResult(props.selectedNodes);
  }
  let chatMode = modelResult.reduce((acc, r) => acc || r.tokens.reduce((acc, t) => acc || t.tag, false), false)

  let countedResults = []
  let variableCountIds = {}

  for (let r of modelResult) {
    let varCounter = 0;
    let result = []
    for (let segment of r.tokens) {
      // determine base variable name
      let baseVariableName = segment.variable
      if (segment.variable.endsWith("]")) {
        baseVariableName = segment.variable.substr(0, segment.variable.indexOf("["))
      }

      if (segment.variable == "__prompt__") {
        if (segment.content.trim() == "") {
          continue;
        }
        result.push({
          variableClassName: "prompt tag-" + segment.tag,
          variable: segment.variable,
          content: segment.content
        })
        continue;
      } else if (segment.variable == "__tag__") {
        result.push({
          variableClassName: "tag",
          variable: "__prompt__",
          content: segment.content
        })
        continue;
      }

      let variableClassName = "v" + (varCounter % 8)
      if (baseVariableName in variableCountIds && props.perVariableColor) {
        variableClassName = "v" + (variableCountIds[baseVariableName] % 8)
      } else {
        variableCountIds[baseVariableName] = varCounter
        varCounter += 1;
      }

      if (segment.tag) {
        variableClassName += " tag-" + segment.tag
      }

      if (segment.variable == "<eos>") {
        variableClassName += " eos"
      }

      result.push({
        variableClassName: variableClassName,
        variable: segment.variable,
        content: segment.content,
      })
    }
    countedResults.push({
      tokens: result,
      node: r.node
    });
  }

  const onDoubleClick = (event) => {
    // select all
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(event.target);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  // sort countedResult by seqlogprob
  countedResults.sort((a, b) => {
    return b.node.data("seqlogprob") - a.node.data("seqlogprob")
  })

  const useTypingAnimation = countedResults.length == 1 && props.trackMostLikly;

  return <ModelResultText style={props.style} onDoubleClick={onDoubleClick} ref={scrollRef} className={chatMode ? "chat-mode" : ""}>
    {countedResults.map((r, i) => {
      return <div key={"result" + i}>
        {countedResults.length > 1 && <h3>
          Result #{i}
          <span className='spacer wide' />
          <span className="variable">
            <span className="badge">seqlogprob</span>
            <span className='spacer' />
            {r.node.data("seqlogprob").toFixed(4)}
          </span>
        </h3>}
        <Truncated tokens={r.tokens} typing={useTypingAnimation} processStatus={props.processStatus} waitingForInput={waitingForInput}></Truncated>
        {chatMode && props.processStatus !== "running" && <div className="system-message">To interact with the model, press 'Run' and type your message.</div>}
        {chatMode && props.processStatus === "running" && waitingForInput === "waiting" && <div className="system-message">Type your message below and press Enter.</div>}
      </div>
    })}
    {countedResults.length == 0 && <EmptyModelResult firstInput={waitingForInput === "waiting"} hasAnyOutput={hasAnyOutput} trackMostLikly={props.trackMostLikly} processStatus={props.processStatus}></EmptyModelResult>}
    <TextInput enabledState={waitingForInput} setEnabledState={setInputState}></TextInput>
  </ModelResultText>
}

function TextInput(props) {
  const [value, setValue] = useState("")
  const [enabledState, setEnabledState] = [props.enabledState, props.setEnabledState]
  const textareaRef = useRef(null)

  // use Enter for send and Shift+Enter for newline
  const onKeyDown = (e) => {
    if (e.key == "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (value.length > 0) {
        LMQLProcess.sendInput(value)
        setValue("")
        setEnabledState("disabled")
      }
    }
  }

  // on change of enabledState
  useEffect(() => {
    if (enabledState == "waiting") {
      window.setTimeout(() => {
        textareaRef.current.focus()
      }, 50)
    }
  }, [enabledState])

  if (enabledState == "hidden") {
    return null;
  }

  return <div className={"chat-input" + (enabledState == "disabled" ? " disabled" : "")}>
    <textarea placeholder="Input" type="text" value={value} onChange={(e) => setValue(e.target.value)} ref={textareaRef} disabled={enabledState == "disabled"} onKeyDown={onKeyDown}></textarea>
    <FancyButton onClick={() => {
      if (enabledState == "disabled") {
        return;
      }
      if (value.length > 0) {
        LMQLProcess.sendInput(value)
        setValue("")
        setEnabledState("disabled")
      }
    }} disabled={enabledState == "disabled"}>
    <BsSendFill/>
    </FancyButton>
  </div>
}

function EmptyModelResult(props) {
  if (props.processStatus == "running" && props.trackMostLikly) {
    return <CenterBox>
      {props.firstInput ? <h2>
        Interactive Mode<br/>
        <span className="subtitle">Type your message below and and press Enter to send.</span>
      </h2> : <h2>
      <LMQLSpinner/>
      Waiting for first tokens...
      </h2>}
    </CenterBox>
  } else if (!props.hasAnyOutput) {
    return <CenterBox>
      <span className="subtitle">Press 'Run' to see model output.</span> 
    </CenterBox>
  } else {
    return <CenterBox>
      <h2>No Selection</h2>
      <span className="subtitle">Select a node in the Decoding Graph to see more details or <span className="link" onClick={() => trackingState.setTrackMostLikely(true)}>Show Latest</span>.</span> 
    </CenterBox>
  }
}

const OutputText = styled.textarea`
  font-size: 9pt;
  font-family: monospace;
  background-color: #222;
  padding: 0;

  &.simple {
    flex: 0;
    border-top: 1px solid #444;
    padding-top: 10pt;
    display: none !important;
  }

  &.simple.always {
    flex: 0.4;
    height: 40pt;
    display: flex !important;
  }
`
const CompiledCodeEditorContainer = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
`


function CompiledCodePanelContent(props) {
  const [compiledCode, setCompiledCode] = useState("# Press Run to compile.");

  // on mount
  useEffect(() => {
    const renderer = {
      add_result: (data) => {
        if (data.type == "compiled-code") {
          setCompiledCode(data.data.code);
        } else {
          // nop in this component
        }
      },
      clear_results: () => setCompiledCode("Compiling..."),
    }
    
    LMQLProcess.addRenderer(renderer)
    return () => {
      LMQLProcess.remove("render", renderer)
    }
  }, []);

  const handleEditorDidMount = (editor, monaco) => {
    ResizeObservers.addResizeListener(() => {
      window.setTimeout(() => {
        editor.layout()
      }, 100)
    })
  }

  return <CompiledCodeEditorContainer {...props}>
  <EditorContainer style={{height: "100%"}}>
  <Editor
      defaultValue={compiledCode}
      theme="vs-dark"
      value={compiledCode}
      // no minimap
      options={{
        // no minimap
        minimap: { enabled: false },
        lineNumbers: "on",
        fontSize: 10,
        readOnly: true,
        wordWrap: "on",
      }}
      defaultLanguage="python"
      onMount={handleEditorDidMount}
    />
  </EditorContainer>  
  </CompiledCodeEditorContainer>
}

const CenterBox = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  text-align: center;
  height: 100%;

  & > h2 {
    margin: 0;
    font-size: 10pt;
    /* lighter than grey */
    color: #888;
    font-weight: normal;
    /* move up by line height */
    margin-top: -30pt;
  }
`

const CollapsiblePanelDiv = styled.div`
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: auto;
  flex: 1;

  h3 {
    display: block;
    padding: 5pt 2pt;
    margin: 5pt 0pt;
    cursor: pointer;
    user-select: none;
  }

  /* hover */
  h3:hover {
    background-color: #333;
  }

  > div {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
`

function CollapsiblePanel(props) {
  const [collapsed, setCollapsed] = useState(true);
  const [height, setHeight] = useState("auto");

  const toggle = () => {
    setCollapsed(!collapsed);
    setHeight(collapsed ? "auto" : "32pt");
  }

  return <CollapsiblePanelDiv style={{ height: height }}>
    <h3 onClick={toggle}>{collapsed ? "▶ " : "▼ "}{props.title}</h3>
    <div className="textview" style={{ display: collapsed ? "none" : "flex" }}>
      {props.children}
    </div>
  </CollapsiblePanelDiv>
}

function resolve(o, path) {
  if (Array.isArray(path)) {
    return path[1];
  }

  try {
    let segements = path.split(".");
    let value = o;
    for (let i = 0; i < segements.length; i++) {
      value = value[segements[i]];
    }
    return value;
  } catch (e) {
    return null
  }
}

function unpack(object, key) {
  if (key in object == false) {
    return object
  }
  if (object[key] == "None") {
    return object
  }

  let o = Object.assign({}, object)
  // delete key
  delete o[key]
  // top-level assign key
  o = Object.assign(o, object[key])
  return o
}

const squareSpan = styled.span`
  display: inline-block;
  width: 8pt;
  height: 8pt;
  margin-right: 5pt;
  border-radius: 2pt;
  position: relative;
  top: 1pt;
  left: 1pt;
`

const VarTrueSquare = styled(squareSpan)`
  background-color: #aaedaa;
`
const VarFalseSquare = styled(squareSpan)`
  background-color: #f09d9d;
`
const FinTrue = styled(squareSpan)`
  background-color: #67f467;
`
const FinFalse = styled(squareSpan)`
  background-color: #eb5943;
`

const ValidLink = styled.a`
  cursor: pointer;
  :hover {
    text-decoration: underline;
  }

  svg {
    position: relative;
    top: 1.5pt;
    margin-left: 3pt;
    margin-right: 3pt;
  }
`

function ValidText(props) {
  const valid = props.valid;
  const final = props.final;

  const squares = {
    "var(true)": <VarTrueSquare />,
    "var(false)": <VarFalseSquare />,
    "var(None)": <VarFalseSquare />,
    "fin(true)": <FinTrue />,
    "fin(false)": <FinFalse />
  }

  const s = `${final}(${valid})`
  const square = squares[s] ? squares[s] : <></>

  if (valid === null || final === null) {
    return <>n/a</>
  } else {
    return <ValidLink onClick={props.onOpenValidationGraph}>
      {square}
      {s}
      <BsArrowRightCircle size={12}/>
      </ValidLink>
  }
}

const ScrollingContent = styled.div`
  flex: 1;
  overflow-y: auto;
  &::-webkit-scrollbar { width: 0pt !important }
  & { overflow: -moz-scrollbars-none; }
  & { -ms-overflow-style: none; }
`

function InspectorPanelContent(props) {
  let nodeInfo = unpack(props.nodeInfo, "user_data")
  nodeInfo = unpack(nodeInfo, "head")

  const valid = ["valid", <ValidText final={resolve(nodeInfo, "final")} valid={resolve(nodeInfo, "valid")} onOpenValidationGraph={props.onOpenValidationGraph}/>]

  const DECODER_KEYS = ["logprob", "seqlogprob", "pool", "prompt"]
  const INTERPRETER_KEYS = ["variable", valid, "mask", "head_index"]
  const PROGRAM_VARIABLES = resolve(nodeInfo, "program_state") ? Object.keys(resolve(nodeInfo, "program_state"))
    .map(key => [key, resolve(nodeInfo, "program_state." + key)]) : []

  const KEYS_TO_FILTER = ["user_data", "parent", "layouted", "label", "id", "full_text", "program_state", "program_variables", "valid", "final", "text", "trace", "root", "seqtext", "where"]

  const decoderKeys = DECODER_KEYS.filter(key => typeof resolve(nodeInfo, key) !== "undefined")
  const interpreterKeys = INTERPRETER_KEYS.filter(key => typeof resolve(nodeInfo, key) !== "undefined")
  const keysFirst = decoderKeys.concat(interpreterKeys).concat(PROGRAM_VARIABLES)

  const keysRest = Object.keys(nodeInfo).filter(key => !keysFirst.includes(key) && !KEYS_TO_FILTER.includes(key) && !key.startsWith("_")).sort()

  const renderLine = (key) => {
    if (Array.isArray(key)) {
      return <tr key={key[0]}><td><h4>{key[0]}</h4></td><td className="value">{key[1]}</td></tr>
    }
    // if key is (key,value) pair then use key as label
    let value = resolve(nodeInfo, key)
    return <tr key={key}><td><h4>{key}</h4></td><td className="value">{"" + JSON.stringify(value)}</td></tr>
  }

  return <DataListView style={{ overflow: "auto", flex: 1, 
    position: "absolute",
    top: "30pt",
    left: "10pt",
    right: "40pt",
    bottom: "10pt"}}>
    <ScrollingContent>
      <table>
        <tbody>
          <tr className="header"><td><h3>Decoder</h3></td><td></td></tr>
          {decoderKeys.map(renderLine)}
          <tr className="header"><td><h3>Interpreter</h3></td><td></td></tr>
          {interpreterKeys.map(renderLine)}
          <tr className="header"><td><h3>Variables</h3></td><td></td></tr>
          {PROGRAM_VARIABLES.map(renderLine)}
          {PROGRAM_VARIABLES.length === 0 && <tr><td><h4>-</h4></td><td></td></tr>}
          {keysRest.length > 0 && <tr className="header"><td><h3>Misc</h3></td><td></td></tr>}
          {keysRest.map(renderLine)}
        </tbody>
      </table>
      <CollapsiblePanel title="Raw Data">
        <div disabled={true} style={{ resize: "none", flex: 1, minHeight: "120pt" }}>
          {JSON.stringify(props.nodeInfo, null, 2)}
        </div>
      </CollapsiblePanel>
    </ScrollingContent>
  </DataListView>
}

function InspectorPane(props) {
  const stretch = props.stretch ?? false;
  const defaultClass = stretch ? 'stretch' : '';
  const nodeInfo = props.nodeInfo && props.nodeInfo.text ? props.nodeInfo : null;

  const [activeTab, _setActiveTab] = useState("inspector");
  const visible = activeTab != null

  const setActiveTab = (tab) => {
    if (tab == activeTab) {
      _setActiveTab(null)
    } else {
      _setActiveTab(tab)
    }
  }

  const tabNames = {
    "inspector": "Inspector",
    "validation": "Validation Graph",
    null: "Inspector"
  }

  let where = null;
  if (props.nodeInfo && props.nodeInfo.user_data && props.nodeInfo.user_data.head) {
    where = props.nodeInfo.user_data.head.where
    // copy via JSON
    if (where) {
      where = JSON.parse(JSON.stringify(where))
    }
  }

  return (
    <Panel className={visible ? defaultClass + " with-sidebar" : 'hidden with-sidebar'} id="inspector">
      <h2>{tabNames[activeTab]}</h2>
      {activeTab == "inspector" && nodeInfo && <InspectorPanelContent nodeInfo={nodeInfo} onOpenValidationGraph={() => setActiveTab("validation")}/>}
      {activeTab == "inspector" && visible && nodeInfo == null && <CenterBox>
        <h2>No Selection</h2>
        <span className="subtitle">Select a node in the Decoding Graph to see more details.</span>
      </CenterBox>}
      <ValidationGraph style={{ 
        position: "absolute",
        top: "30pt",
        left: "10pt",
        right: "40pt",
        bottom: "10pt",
        visibility: activeTab == "validation" ? "visible" : "hidden"}} graph={where}/>
      <Sidebar>
        <IconButton
          onClick={() => setActiveTab("inspector")}
          className={activeTab == "inspector" ? 'active' : ''}>
          <BsCardList size={16} />
        </IconButton>
        <IconButton
          onClick={() => setActiveTab("validation")}
          className={activeTab == "validation" ? 'active' : ''}>
          <BsCheckSquare size={16} />
        </IconButton>
      </Sidebar>
    </Panel>
  );
}

const LMQLSpinnerDiv = styled.div`
  &.lmql-spinner {
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
  .pt1 {
    color: white;
    animation: pulse 2s infinite;
    position: absolute;
    top: -6pt;
    left: 2pt;
  } 
  .pt2 {
    color: white;
    font-size: 12pt;
    position: absolute;
    top: -2.5pt;
    right: 2pt;
    animation: pulse 2s infinite;
    animation-delay: 1s;
  }
  
  .pt3 {
    position: absolute;
    bottom: -5pt;
    right: 0pt;
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
`

function LMQLSpinner() {
  return <LMQLSpinnerDiv className="lmql-spinner">
    <span className='pt1'>*</span>
    <span className='pt2'>&gt;</span>
    <span className='pt3'></span>
  </LMQLSpinnerDiv>
}


function SidePanel(props) {
  const stretch = props.stretch ?? false;
  const defaultClass = stretch ? 'stretch' : '';
  const clearTrigger = useState(new TriggerState())[0];
  const [clearOnRun, setClearOnRun] = useState(true);
  const [perVariableColor, setPerVariableColor] = useState(true);

  const [trackMostLikly, setTrackMostLiklyInternal] = useState(window.localStorage.getItem("trackMostLikely") === "true");
  trackingState.setTrackMostLikely = setTrackMostLiklyInternal
  trackingState.getTrackMostLikely = () => trackMostLikly
  const setTrackMostLikly = (value) => {
    setTrackMostLiklyInternal(value)
    window.localStorage.setItem("trackMostLikely", value)
    if (!value && props.mostLikelyNode) {
      trackingState.setSelectedNode(props.mostLikelyNode)
    }
  }

  const [sidepanel, setSidepanel] = useState("model");
  const setSidepanelTo = (panel) => {
    if (sidepanel === panel && props.simpleMode) {
      setSidepanel(null);
    } else {
      setSidepanel(panel);
    }
  }

  // when click "Check Output" change the sidepanel to output
  errorState.showErrorOutput = () => {
    setSidepanel("output")
  }

  const visible = sidepanel != null;

  useEffect(() => {
    LMQLProcess.on('run', () => {
      if (clearOnRun) {
        clearTrigger.trigger();
      }
    })
  }, [clearTrigger, clearOnRun])

  const titles = {
    "output": "Output",
    "code": "Compiled Code",
    "model": "Model Response",
    "stats": "Statistics"
  }

  return (
    <Panel className={visible ? defaultClass + " with-sidebar" : 'hidden with-sidebar'} id="sidepanel">
      <h2>
        {titles[sidepanel]}
        {sidepanel == 'output' && <>
          <ToolbarSpacer />
          <ToolbarIconButton onClick={() => clearTrigger.trigger()}>
            <BsXCircle size={8} />
            <span>Clear</span>
          </ToolbarIconButton>
          <ToolbarIconButton className={clearOnRun ? "checked checkable" : "checkable"} onClick={() => setClearOnRun(!clearOnRun)}>
            {clearOnRun ? "Clears on Run" : "Clear on Run"}
          </ToolbarIconButton>
        </>}
        {sidepanel == 'model' && <>
          <ToolbarSpacer />
          <CheckableToolbarIconButton checked={perVariableColor} onClick={() => setPerVariableColor(!perVariableColor)}>
            Color By Variable
          </CheckableToolbarIconButton>
          
          {props.simpleMode &&
            <CheckableToolbarIconButton checked={trackMostLikly} onClick={() => setTrackMostLikly(!trackMostLikly)}>
              Show Latest
            </CheckableToolbarIconButton>
          }
        </>}
      </h2>
      <CompiledCodePanelContent style={{ display: sidepanel === 'code' ? 'block' : 'none' }} />
      <ModelResultContent style={{ display: sidepanel === 'model' ? 'flex' : 'none' }}
        selectedNodes={props.selectedNodes}
        perVariableColor={perVariableColor}
        mostLikelyNode={props.mostLikelyNode}
        trackMostLikly={trackMostLikly || !props.simpleMode}
        onTrackLatest={() => setTrackMostLikly(true)}
        processStatus={props.processStatus}
      />
      <OutputPanelContent 
        className={!props.simpleMode && sidepanel != 'output' ? "simple" : ""} 
        style={{ display: ((!props.simpleMode) || sidepanel === 'output') ? 'block' : 'none' }} 
        clearTrigger={clearTrigger} 
      />
      {/* <StatisticsPanelContent style={{display: sidepanel === 'stats' ? 'flex' : 'none'}}/> */}

      <Sidebar>
        {displayState.mode == "embed" && displayState.embedFile && <IconButton onClick={() => window.open(window.location.href.split('?')[0] + "?snippet=" + displayState.embedFile, "_blank")}>
          <BsBoxArrowUpRight size={16} />
        </IconButton>}
        <IconButton onClick={() => setSidepanelTo('model')} className={sidepanel === 'model' ? 'active' : ''}>
          <BsFillChatLeftTextFill size={16} />
        </IconButton>
        <IconButton
          onClick={() => setSidepanelTo('output')}
          className={sidepanel === 'output' ? 'active' : ''}>
          <BsTerminal size={16} />
        </IconButton>
        <IconButton onClick={() => setSidepanelTo('code')} className={sidepanel === 'code' ? 'active' : ''}>
          <BsFileCode size={16} />
        </IconButton>
        {/* <IconButton onClick={() => setSidepanelTo('stats')} className={sidepanel === 'stats' ? 'active' : ''}>
          <BsFileBarGraph size={16}/>
        </IconButton> */}
        <ToolbarSpacer/>
        {displayState.mode == "embed" && <IconButton className="bottom" onClick={() => OpenAICredentialsState.setOpen(true)}>
          <BsGear size={16} />
        </IconButton>}
      </Sidebar>
    </Panel>
  );
}

const Toolbar = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 0pt;

  .bottom {
    margin-top: 40pt;
  }

  >a {
    display: block;
    margin: 4pt;
    margin-left: 8pt;
    font-size: 10pt;
    color: black;

    text-decoration: none;

    @media screen and (max-width: 40em) {
      display: none;
    }

    :hover {
      text-decoration: underline;
    }
  }
`

const ButtonGroup = styled.div`
  display: flex;
  background-color: ${bg};
  padding: 4pt;
  padding-left: 2pt;
  flex-direction: row;
  justify-content: flex-start;
  z-index: 1;
  
  /* position: absolute;
  bottom: 10pt;
  left: 10pt;
  width: calc(100% - 20pt); */
`

const FancyButton = styled.button`
  /* blue purpleish button gardient */
  background-color: #6b77ff;
  border: 0pt solid #6b77ff;
  padding: 8pt 10pt;
  font-size: 10pt;
  border-radius: 2pt;
  font-weight: bold;
  color: white;

  :hover {
    /* border: 1pt solid #8e98ea; */
    background-color: #a5acfa;
    cursor: pointer;
  }

  &.green {
    background-color: #5db779;
    border-color: #5db779;

    :hover {
      background-color: #458a5b;
    }

    &:disabled {
      background-color: #5db77a31;
      border-color: transparent;
      color: #ffffff44;

      :hover {
        cursor: default;
        background-color: #5db77a31;
        border-color: transparent;
        color: #ffffff44;
      }
    }
  }

  @media (max-width: 50em) {
    &.in-toolbar {
      position: absolute;
      bottom: 20pt;
      right: 20pt;
      z-index: 999;

      box-shadow: 0 0 40pt 0pt #100f1f44;
    }
  }
`

// Action button derivative with red color
const StopButton = styled(FancyButton)`
  border-color: #ff0000;
  background: none;
  /* off red */
  background-color: transparent;
  display: inline;
  border: none;
  color: #c4c2c2;
  text-align: left;
  margin-left: 2pt;
  margin-right: 0;
  position: relative;
  bottom: 0.5pt;
  padding: 4pt !important;

  // hover highlight
  &:hover {
    // slightly darker than background
    text-decoration: underline;
    background: none;
    background-color: transparent;
    color:white;
    border: none;
  }

  // click highlight
  &:active {
    background: none;
    // slightly darker than hover
    background-color: transparent;
  }

  &:disabled {
    display: none;
  }

  &:hover:disabled {
    background-color: transparent;
    cursor: default;
    border: none;
  }

  &.light {
    color: #404040;

    :hover {
      color: #404040;
    }
  }
`

const Spacer = styled.div`
  flex: 1;
`

const ToolbarSpacer = styled.div`
  flex: 1;
  display: inline;
`

class TriggerState {
  constructor(listener = null) {
    this.listener = listener;
  }

  trigger() {
    if (this.listener) {
      this.listener(...arguments)
    }
  }

  addTriggerListener(listener) {
    this.listener = listener;
  }
}

function DecoderPanel(props) {
  const fitTrigger = useState(new TriggerState())[0];
  const [eagerLayout, setEagerLayout] = useState(false);

  const derivedNodeFeatures = (data) => {
    return {
      "_finfalse": data.user_data && data.user_data.head && data.user_data.head.valid == "False",
      "_isRoot": data.root,
      "_isDone": data.user_data && data.user_data.head && data.user_data.head.variable == "__done__",
      "_noUserData": !data.user_data || (data.user_data && data.user_data == "None")
    }
  }

  return <Panel className='stretch' id="decoder">
    <h2>
      Decoder Graph
      <ToolbarSpacer />
      <ToolbarIconButton onClick={() => fitTrigger.trigger()}>
        <BsFullscreen size={8} />
        <span>Fit</span>
      </ToolbarIconButton>
      <ToolbarIconButton className={eagerLayout ? "checked checkable" : "checkable"} onClick={() => setEagerLayout(!eagerLayout)}>
        {eagerLayout ? <BsCheckSquare size={8} /> : <BsSquare size={8} />}
        <span className="spacer wide"> </span>
        Eager Layouting
      </ToolbarIconButton>
    </h2>
    <DecoderGraph 
      fitTrigger={fitTrigger} 
      onSelectNode={props.onSelectNode} 
      eagerLayout={eagerLayout}
      onMostLiklyNode={props.onMostLiklyNode} 
      derivedNodeFeatures={derivedNodeFeatures}
      selectedNodeTrigger={props.selectedNodeTrigger}
    />
  </Panel>
}

const StatusCircle = styled.div`
  width: 5pt;
  height: 5pt;
  border-radius: 2.5pt;
  background-color: #47CF73;
  margin-right: 5pt;

  &.pulsing {
    animation: pulsing 1s infinite alternate;
  }

  /* pulsing animation */
  @keyframes pulsing {
    0% {
      opacity: 0;
    }
    100% {
      opacity: 1;
    }
  }
`

const StatusLightContainer = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  font-size: 8pt;
  margin-top: 0pt;
  margin-left: 10pt;
`

function StatusLight(props) {
  let [firstStartup, setFirstStartup] = useState(true);

  props = Object.assign({
    connected: false,
    label: 'Disconnected',
  }, props.connectionState);

  let label = props.status || props.label;
  if (label == "idle" || label == "secret-missing") {
    label = "Ready"
    props.connected = true
    if (firstStartup) {
      setFirstStartup(false);
    }
  } else if (label == "running") {
    label = "Running"
    props.connected = true
  } else if (label == "stopping") {
    label = "Stopping..."
    props.connected = true
  } else if (label == "init") {
    if (!firstStartup) {
      label = "Reloading " + (props.error ? props.error : "") + "..."
    } else {
      label = "Loading " + (props.error ? props.error : "") + "..."
    }
  }

  let statusColor = props.connected ? '#5db779' : '#a0a0a0';

  return <StatusLightContainer>
    <div className='status-light'></div>
    {label != "" && <StatusCircle style={{ backgroundColor: statusColor }} className={!props.connected ? "pulsing" : ""} />}
    <span style={{ color: statusColor, marginRight: "10pt" }}>{label}</span>
  </StatusLightContainer>
}

const Commit = styled.div`
  margin-left: 5pt;
  text-align: right;
  font-size: 8pt;
  color: #4c4b4b;
  margin-right: 10pt;

  span {
    color: #4a4a4a;
    opacity: 0.0;
    margin-right: 2pt;
  }

  :hover span { 
    opacity: 1.0;
  }
`

const ToggleButton = styled.button`
  border: none;
  background-color: ${props => props.toggled ? "#00000022" : "transparent"};
  padding: 5pt 7pt;
  border-radius: 4pt;

  span {
    position: relative;
    top: -1.5pt;
    margin-left: 4pt;
  }

  :hover {
    background-color: #0000002E;
  }
`

const OpenAICredentialsState = {
  open: false,
  listeners: [],
  setOpen: function (open) {
    OpenAICredentialsState.open = open;
    this.listeners.forEach((listener) => listener(open));
  }
}


const Explainer = styled.span`
  font-size: 12pt;
  color: #424242;


  a {
    color: #424242;
    text-decoration: underline;
    outline: none;

    :visited {
      color: #424242;
    }
  }

  form {
    margin-top: 20pt;
    margin-bottom: 20pt;
  }
`

function OpenAICredentials() {
  const [open, setOpen] = useState(OpenAICredentialsState.open);
  OpenAICredentialsState.listeners.push(setOpen);
  const [secret, setSecret] = useState(window.localStorage.getItem("openai-secret") || "");

  useEffect(() => {
    const onStatus= s => {
      if (s.status == "secret-missing") {
        OpenAICredentialsState.setOpen(true);
      }
    }
    // try to read transient secret from #anchor
    window.unsalt_key = function(k) {
      // base 64 decode
      k = atob(k)
      return k.split("").map((c, i) => String.fromCharCode(c.charCodeAt(0) ^ salt.charCodeAt(i % salt.length))).join("")
    }
    window.salt_key = function(k) {
      let salted = k.split("").map((c, i) => String.fromCharCode(c.charCodeAt(0) ^ salt.charCodeAt(i % salt.length))).map(c => c.charCodeAt(0))
      // base 64 encode
      salted = btoa(String.fromCharCode(...salted))
      return salted
    }

    const anchor = window.location.hash;
    const salt = "lmql-transient-secret-1237u23"
    if (anchor.startsWith("#key=")) {
      if (LMQLProcess.setSecret) {
        const secret = window.unsalt_key(anchor.slice(5))
        console.log("set transient OpenAI secret to", secret)
        LMQLProcess.setSecret(secret);
      }
    }

    LMQLProcess.on("status", onStatus);
    return () => {
      LMQLProcess.remove("status", onStatus);
    }
  }, []);

  if (!open) {
    return null;
  }

  const onSave = (e) => {
    LMQLProcess.setSecret(secret);
    OpenAICredentialsState.setOpen(false);
  }

  const onCancel = (e) => {
    OpenAICredentialsState.setOpen(false);
  }

  return <PromptPopup>
    <div className="click-handler" onClick={() => OpenAICredentialsState.setOpen(false)}/>
    <Dialog className={displayState.mode == "embed" ? "embed" : ""}>
      <h1>OpenAI Credentials</h1>
      <Explainer>
        <p>
          To run your own queries in the LMQL playground, you have to provide your OpenAI API key. The key will only be stored in your browser's <a href="https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage" target="_blank" rel="noreferrer">local storage</a>. You can find your API key in the <a href="https://beta.openai.com/account/api-keys" target="_blank" rel="noreferrer">OpenAI dashboard</a>.<br />
        </p>
        <p className='note'>
          <b>Note:</b> LMQL will use your API key to execute completion requests on your behalf. This will result in charges on your OpenAI account. Please make sure you understand the <a href="https://beta.openai.com/pricing" target="_blank" rel="noreferrer">OpenAI pricing model</a> before using LMQL. <i>LMQL does not take responsibility for any charges incurred by executing queries on this site.</i>
        </p>
        <form onSubmit={onSave}>
          <label>OpenAI API Secret</label><br />
          <input type="password" placeholder="API Secret" id="openai-api-key" onChange={(e) => setSecret(e.target.value)} value={secret} />
          {secret.length > 0 && <button onClick={(e) => { e.preventDefault(); setSecret("") }}>Clear</button>}
        </form>
        
      </Explainer>
      <div>
        <FancyButton className='blue' onClick={onSave}>
          <span>Save</span>
        </FancyButton>
        <StopButton className="light" onClick={onCancel}>
          Cancel
        </StopButton>
      </div>

    </Dialog>
  </PromptPopup>
}

const TopBarMenu = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  position: absolute;
  display: none;
  z-index: 100;
  top: 32pt;
  right: 0pt;
  width: 150pt;
  height: auto;
  background-color: white;
  border-radius: 4pt;
  border: 0.4pt solid grey;

  box-shadow: 0 0 10pt 0 #a2a1a11b;

  &.visible {
    display: block;
  }

  li a {
    text-decoration: none;
    color: black;
    display: block;

    :visited {
      color: black;
    }
  }

  li, >span {
    height: 15pt;
    line-height: 15pt;
    text-align: left;
    padding: 4pt;
    padding-left: 8pt;
    cursor: pointer;

    :hover {
      background-color: #00000022;
    }
  }

  li svg {
    position: relative;
    top: 1pt;
    margin-right: 2pt;
  }

  li a svg {
    margin-right: 5pt;
  }

  >span {
    color: #acacac;
    display: block;
    height: auto;
    font-size: 8pt;
    cursor: default;
    text-align: center;
    padding-right: 8pt;
    line-height: 1.2em;
    border-top: 0.4pt solid #dedddd;

    :hover {
      background-color: transparent;
    }
  }
`

// App as class component
class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      selectedNodeInfo: null,
      selectedNode: null,
      selectedNodes: null,

      mostLikelyNode: null,
      selectedNodeTrigger: new TriggerState(),

      buildInfo: BUILD_INFO.info(),
      status: LMQLProcess.status,
      processState: "init",
      graphLayout: false,
      topMenuOpen: false,
      // true by default, false if local storage is set
      simpleMode: window.localStorage.getItem("simple-mode") == "true",

      /* show code screenshot overlay */
      codeScreenshot: false
    }
  }

  setSimpleMode(simpleMode) {
    window.localStorage.setItem("simple-mode", simpleMode);
    ResizeObservers.notify();
    this.setState({ simpleMode });
  }

  setSelectedNodeInfo(selectedNodeInfo) {
    if (!selectedNodeInfo) {
      this.setState({ selectedNodeInfo: null });
      return;
    }
    this.setState({ selectedNodeInfo: selectedNodeInfo });
  }

  setTopMenuOpen = (open) => {
    this.setState({ topMenuOpen: open });
  }

  setSelectedNode(selectedNode) {
    if (!selectedNode) {
      this.setState({ selectedNode: null });
      return;
    }
    this.setState({ selectedNode });
  }

  setSelectedNodes = (selectedNodes) => {
    if (!selectedNodes) {
      this.setState({ selectedNodes: null });
      return;
    }
    this.setState(state => Object.assign({}, state, {
      selectedNodes: selectedNodes(state.selectedNodes)
    }))
  }

  setMostLikelyNode = (mostLikelyNode) => {
    this.setState({ mostLikelyNode });
  }

  setBuildInfo(buildInfo) {
    this.setState({ buildInfo });
  }

  setStatus = (status) => {
    this.setState({ status });
  }

  setProcessState = (processState) => {
    this.setState({ processState });
  }

  setGraphLayout(graphLayout) {
    this.setState({ graphLayout });
    ResizeObservers.notify();
  }

  // conform to renderer interface
  add_result(r) {}

  clear_results() {
    this.setSelectedNodeInfo(null)
    this.setSelectedNode(null)
    this.setMostLikelyNode(null)
    this.setSelectedNodes(null)
  }

  onStatus(event) {
    if (event.status == "running" || event.status == "error") {
      this.setProcessState("running")
    } else {
      this.setProcessState("idle")
    }
  }

  componentDidMount() {
    LMQLProcess.addConsoleListener(console.log)
    LMQLProcess.on("status", s => this.setStatus(s))
    LMQLProcess.addRenderer(this)
    LMQLProcess.addStatusListener(this.onStatus.bind(this))

    BUILD_INFO.addListener(this.setBuildInfo.bind(this))

    // when document browser scale is changed
    window.addEventListener("resize", ResizeObservers.notify)
    
    this.onKeyDown = this.onKeyDown.bind(this)
    window.addEventListener("keydown", this.onKeyDown)
  }

  onKeyDown(event) {
    /* On R*/
    if (event.keyCode == 82 && event.ctrlKey) {
      this.onRun();
    }
    /* On Escape */
    if (event.keyCode == 27) {
      LMQLProcess.kill();
    }
  }

  componentWillUnmount() {
    LMQLProcess.remove("render", this)
    LMQLProcess.remove("status", this.onStatus.bind(this))
    
    window.removeEventListener("resize", ResizeObservers.notify)
    window.removeEventListener("keydown", this.onKeyDown)
  }

  onExportState() {
    let graphData = persistedState.dump()
    let dataUrl = "data:text/json;charset=utf-8," + encodeURIComponent(graphData)
    // trigger download of data
    let a = document.createElement('a');
    a.setAttribute("href", dataUrl);
    a.setAttribute("download", "lmql-state.json");
    a.click();
  }

  onRun() {
    const code = persistedState.getItem("lmql-editor-contents");
    const model = persistedState.getItem("playground-model");
    const appData = {
      "name": "lmql",
      // monaco get editor content
      "app_input": code,
      "app_arguments": [{
        "model": model
      }]
    };

    LMQLProcess.run(appData);
  }

  onSelectNode(node, additive = false) {
    trackingState.setTrackMostLikely(false)

    this.setSelectedNode(node);
    this.setSelectedNodeInfo(node ? node.data() : null);

    this.setSelectedNodes((n) => {
      if (n == null) {
        return [node]
      } else if (additive) { // additive && n != null
        if (!n.includes(node)) {
          return [...n, node]
        } else {
          return n
        }
      } else {
        return [node]
      }
    })
  };

  onMostLiklyNode(node) {
    if (node == null) { return }
    this.setMostLikelyNode(node)
  };

  getCodeScreenshotInput() {
    let modelResult = null;
    if (trackingState.getTrackMostLikely()) {
      modelResult = reconstructTaggedModelResult([this.state.mostLikelyNode]);
    } else {
      modelResult = reconstructTaggedModelResult(this.state.selectedNodes);
    }
    return {
      "code": persistedState.getItem("lmql-editor-contents"),
      "model_result": modelResult,
    }
  }

  onCodeScreenshot() {
    this.setState({ codeScreenshot: true })
  }

  hideCodeScreenshot() {
    this.setState({ codeScreenshot: false })
  }

  render() {
    trackingState.setSelectedNode = n => {
      this.onSelectNode(n)
      this.state.selectedNodeTrigger.trigger(n)
    };

    const simpleModeClassName = (this.state.simpleMode && displayState.mode != "embed") ? "" : "simple-mode";

    return (
      <ContentContainer className={this.state.graphLayout ? 'graph-layout' : ''}>
        {displayState.mode != "embed" && <Toolbar>
          <Title>
            <img src="/lmql.svg" alt="LMQL Logo"/>  
            LMQL Playground
            {configuration.NEXT_MODE && <span className="badge">PREVIEW</span>}
          </Title>
          {configuration.DEMO_MODE && <FancyButton className="in-toolbar" onClick={() => ExploreState.setVisibility(true)}>
            <ExploreIc/> 
            {!configuration.NEXT_MODE && <>Explore LMQL</>}
            {configuration.NEXT_MODE && <>Explore New Features</>}
          </FancyButton>}
          {window.location.hostname.includes("lmql.ai") && <a href={"https://docs.lmql.ai/en/latest/quickstart.html"} target="_blank" rel="noreferrer" className="hidden-on-small">
          Install LMQL Locally </a>}
          <Spacer />
          {/* show tooltip with build time */}
          {/* trigger button */}
          {/* <ToggleButton onClick={() => this.setGraphLayout(!this.state.graphLayout)} toggled={this.state.graphLayout}>
            <BsLayoutWtf size={14} />
          </ToggleButton> */}
          <ToggleButton onClick={() => this.setSimpleMode(!this.state.simpleMode)} toggled={this.state.simpleMode} className="hidden-on-small">
            <BsGridFill size={14} />
            <span>
              Advanced Mode
            </span>
          </ToggleButton>
          {/* settings button */}
          <Commit>{this.state.buildInfo.commit}</Commit>
          <ToggleButton onClick={() => this.setTopMenuOpen(!this.state.topMenuOpen)} toggled={this.state.topMenuOpen}>
            <BsGear size={14} />
            <TopBarMenu className={this.state.topMenuOpen ? 'visible' : ''}>
              {configuration.BROWSER_MODE && <li onClick={() => OpenAICredentialsState.setOpen(true)}>
              <BsKeyFill/> OpenAI Credentials
              </li>}
              {configuration.DEV_MODE && <li onClick={() => this.onExportState()}><BsFileArrowDownFill/> Export State</li>}
              {configuration.DEV_MODE && <li onClick={() => this.onCodeScreenshot()}><BsFillCameraFill/> Code Screenshot</li>}
              <li>
                <a href="https://github.com/eth-sri/lmql" disabled target="_blank" rel="noreferrer"><BsGithub/>LMQL on Github</a>
              </li>
              <li>
                <a href="https://docs.lmql.ai" disabled target="_blank" rel="noreferrer"><BsBook/>Documentation</a>
              </li>
              <span>
                LMQL {this.state.buildInfo.commit} 
                {(configuration.BROWSER_MODE && !isLocalMode()) && <> In-Browser</>}
                {isLocalMode() && <> Self-Hosted</>}
                {this.state.buildInfo.date != "-" ? <>
                  <br/>
                  Build on {this.state.buildInfo.date}
                </> : null}
              </span>
            </TopBarMenu>
          </ToggleButton>
        </Toolbar>}
        <Row className={simpleModeClassName + " simple"}>
          <EditorPanel onRun={this.onRun.bind(this)} processState={this.state.status} connectionState={this.state.status} />
          <SidePanel selectedNodeInfo={this.state.selectedNodeInfo} selectedNode={this.state.selectedNode} selectedNodes={this.state.selectedNodes} mostLikelyNode={this.state.mostLikelyNode} processStatus={this.state.processState} simpleMode={this.state.simpleMode}/>
        </Row>
        <Row style={{ flex: 1 }} className={simpleModeClassName}>
          <DecoderPanel onSelectNode={this.onSelectNode.bind(this)} onMostLiklyNode={this.onMostLiklyNode.bind(this)} selectedNodeTrigger={this.state.selectedNodeTrigger} />
          <InspectorPane nodeInfo={this.state.selectedNodeInfo}></InspectorPane>
        </Row>
        <OpenAICredentials />
        {configuration.DEMO_MODE && displayState.mode != "embed" && <Explore />}
        {this.state.codeScreenshot && <CodeScreenshot hide={this.hideCodeScreenshot.bind(this)} {...this.getCodeScreenshotInput()}/>}
      </ContentContainer>
    );
  }
}

export default App;
