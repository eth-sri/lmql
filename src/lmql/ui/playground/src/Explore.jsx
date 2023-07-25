import React, { useEffect, useState } from "react";
import styled from "styled-components";
import {queries} from "./queries";
import { displayState, persistedState, trackingState } from "./State";
import {configuration} from "./Configuration"

import { BUILD_INFO } from './build_info';
import { isLocalMode} from './Configuration';

export const PromptPopup = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: #000000c2;
  z-index: 999;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  animation: fade-in 0.2s;

  @keyframes fade-in {
    0% {
      opacity: 0;
    }
    100% {
      opacity: 1;
    }
  }

  .click-handler {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
  }
`

export const Dialog = styled.div`
  background-color: #ffffff;
  border-radius: 4pt;
  overflow: hidden;
  padding: 10pt;
  margin: auto;
  max-width: 1100pt;
  max-height: 500pt;
  color: black;

  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica;

  input {
    border: none;
    background-color: #dfdfdf;
    border-radius: 4pt;
    font-size: 14pt;
    outline: none;
    padding: 5pt;
    margin: 10pt;
    margin-left: 0pt;
    border: 2pt solid transparent;

    :focus {
      border: 2pt solid #8e98ea;
    }
  }

  &.embed {
    width: calc(100% - 22pt) !important;
    margin: 0;
    max-width: 100% !important;
    height: 100%;
    max-height: 100%;
    border: 1pt solid grey;
    font-size: 8pt !important;
  }

  label {
    font-size: 10pt;
    position: relative;
    top: 8pt;
    left: 2pt;
  }
`

const ExploreDialog = styled(Dialog)`
  width: 800pt;
  height: 700pt;
  max-height: calc(100vh - 40pt);
  max-width: 100vw;
  overflow-y: auto;

  /* invisible scroll bar */
  ::-webkit-scrollbar {
    width: 0px;
    background: transparent;
  }

  position: relative;
  padding: 0pt;
  

  @media (max-width: 800pt) {
    border-radius: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    max-height: 100vh !important;
    max-width: 100vw !important;
  }
  

  @media (max-width: 450pt) {
    width: calc(100vw - 20pt);
    height: calc(100vh - 20pt);
    max-height: 100vh;
    max-width: 100vw;
    overflow-y: auto;
    position: relative;
    padding: 10pt;
    padding-bottom: 80pt;
    padding-left: 0;
    margin: 0;

    div.tile {
      display: block !important;
      height: 40pt;
      width: 100% !important;

      &:hover {
        transform: none !important;
        border: 1pt solid #ababab;
      }
    }
  }

  >div {
    padding: 5pt 20pt;
    position: relative;
  }

  >div .sidenote a {
    padding-left: 2pt;
  }

  >div .sidenote {
    position: absolute;
    top: 15pt;
    right: 15pt;
    font-size: 8pt;
  }

  div.highlight {
    background-color: #f5f5f5;
    margin: 5pt;
    border-radius: 4pt;
  }

  >div>div {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
  }

  p {
    text-align: justify;
  }

  h1 {
    margin: 0;
    padding: 20pt;
    font-weight: bold;
    padding-bottom: 10pt;
  }

  h1 img {
    width: 20pt;
    height: 20pt;
    margin-right: 8pt;
    position: relative;
    top: 2pt;
  }

  h2 {
    font-size: 12pt;
  }

  h3 {
    font-size: 12pt;
    color: #373737;
    margin: 0;
    z-index: 999;
    font-weight: 700;
  }

  .close {
    position: absolute;
    top: 10pt;
    right: 10pt;
    width: 30pt;
    height: 30pt;
    text-align: center;
    line-height: 30pt;
    font-size: 20pt;
    cursor: pointer;
  }
`

const Tile = styled.div.attrs({
  className: "tile"
})`
  background-color: white;
  border-radius: 4pt;
  padding: 10pt;
  margin: 10pt;
  margin-left: 0pt;
  margin-top: 0pt;
  cursor: pointer;
  transition: 0.05s ease-in-out transform;
  height: 80pt;
  width: 100pt;
  border: 1pt solid #d4d4d4;
  opacity: 0.9;
  position: relative;
  display: flex;
  flex-direction: column;
  
  align-items: flex-start;
  justify-content: flex-start;

  :hover {
    transform: scale(1.05);
    opacity: 1.0;
    border: 1pt solid #9b9a9a;
  }

  h3 {
    color: #212121;
  }

  code {
    opacity: 0.3;
  }

  p {
    color: #010101;
    font-size: 10pt;
    font-style: italic;
    z-index: 999;
    text-align: left;
  }

  .badge {
    color: #212121;
    position: absolute;
    top: 6pt;
    right: 6pt;
    font-size: 5pt;
    background-color: #e2e0e1;
    padding: 2pt;
    z-index: 9;
  }
`

export const ExploreState = {
    visible: window.location.hash === "#explore",
    setVisibility: (s) => {
        ExploreState.visible = s;
        ExploreState.listeners.forEach((l) => l(s));
    },
    listeners: []
}

// make sure class name is code-container
const CodeContainer = styled.div.attrs({
  className: "code-container"
})`
  background-color: transparent;
  padding: 10pt;
  margin: 0pt;
  overflow: hidden;
  transform: scale(0.8);
  transform-origin: top left;
  max-height: 50pt;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  color: #323232;

  .keyword {
    color: #ff79c6;
    font-weight: bold;
  }

  code {
    width: 1024pt;
    margin: 0;
    padding: 0;
    white-space: pre-wrap;
    color: #f1fa8c;

    font-size: 4pt;
    line-height: 4pt;
    overflow-x: hidden;
    overflow-y: hidden;
    width: 100%;
    max-height: 60pt;
    white-space: pre-wrap;
    display: block;
  }

  /* fade out bottom */
  :after {
    content: "";
    position: absolute;
    bottom: -2px;
    left: 0;
    right: 0;
    height: 20pt;
    /* background: linear-gradient(180deg, transparent 0%, #f5f5f561 100%); */
  }
`

function BasicHighlighted(props) {
  const s = props.code;

  const keywords = ["argmax", "where", "from", "and", "or", "not", "sample", "beam_search"];
  // split into words (also split on ()\t\n)
  const words = s.split(/(\s+|[()\t])/g);
  const result = words.map((w,i) => {
    if (keywords.includes(w.toLowerCase())) {
      return <span key={w + i} className="keyword">{w}</span>
    }
    return <span key={w + i}>{w}</span>
  })
  return <CodeContainer>
    <code>{result}</code>
  </CodeContainer>
}

const Description = styled.p`
  font-size: 14pt;
  color: #696969;
  padding: 0pt 20pt;
  font-weight: 500;
  margin-top: 0pt;
`

const LinkBox = styled.div`
  display: flex;
  flex-direction: row;

  a.button {
    display: block;
    border: 1pt solid #6b77ff;
    padding: 5pt;
    margin-top: 15pt;
    margin-right: 5pt;
    border-radius: 2pt;
    color: #6b77ff;

    font-size: 10pt;
  }

  a.button:first-child {
    color: white;
    background-color: #6b77ff;

    &:hover {
      background-color: #8e98ea;
      text-decoration: none;
    }
  }
`

const CiteBox = styled.code`
  display: block;
  background-color: #f5f5f5;
  padding: 4pt;
  border-radius: 4pt;
`

const PoweredBy = styled.div`
  font-size: 8pt;
  color: #696969;
  text-align: center;
  margin: auto;

  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10pt;

  >div:nth-child(2) {
    margin-left: 5pt;
  }
`

let didLoadAnchor = false;

const PreviewQueries = {
  queries: [],
  listeners: []
}

export function Explore() {
    const [visible, setVisible] = useState(ExploreState.visible);

    const onClickTile = (q) => {
      ExploreState.setVisibility(false);
      if (q.state) {
        fetch(q.state).then((r) => r.text()).then((r) => {
          persistedState.load(r);
          persistedState.setItem("lmql-editor-contents", q.code)
          window.setTimeout(() => trackingState.setTrackMostLikely(true), 10);            
        }).catch((e) => {
          console.error(e)
          alert("Error loading example.")
        });
      } else {
        persistedState.setItem("lmql-editor-contents", q.code)
      }
    }

    let [exploreQueries, setExploreQueries] = useState(configuration.NEXT_MODE ? PreviewQueries.queries : queries);

    useEffect(() => {
      if (configuration.NEXT_MODE) {
        let url = "https://raw.githubusercontent.com/lmql-lang/awesome-lmql/main/next/showcase-playground.js";
        url += "?nocache=" + Math.random();
        fetch(url).then((r) => r.text()).then((r) => {
          // eslint-disable-next-line no-eval
          let queries = eval(r).queries;
          PreviewQueries.queries = queries;
          PreviewQueries.listeners.forEach((l) => l());
          console.log("Loaded list of Preview release queries.", queries)
        }).catch((e) => {
          console.error(e)
          console.error("Error loading list of Preview release queries.")
        });
      }
    }, [])

    useEffect(() => {
        // register listeners
        ExploreState.listeners.push(setVisible);

        // check if first visit
        const editorContents = window.localStorage.getItem("lmql-editor-contents");
        if (editorContents === null || (typeof editorContents === "string" && editorContents.trim().length === 0)) {
          ExploreState.setVisibility(!displayState.preloaded);
        }

        // check for hash-specified example to load
        if (window.location.hash && !didLoadAnchor) {
          didLoadAnchor = true;
          const anchor = window.location.hash.substring(1);
          let matches = queries.filter(c => c.queries.find(q => q.state.includes(anchor)))
          if (matches.length === 1) {
            let query = matches[0].queries.find(q => q.state.includes(anchor))
            window.setTimeout(() => onClickTile(query), 10);
          }
        }

        return () => {
            ExploreState.listeners = ExploreState.listeners.filter((l) => l !== setVisible);
        }
    }, []);

    useEffect(() => {
      if (configuration.NEXT_MODE) {
        const listener = () => {
          setExploreQueries(PreviewQueries.queries);
        }
        PreviewQueries.listeners.push(listener);
        return () => {
          PreviewQueries.listeners = PreviewQueries.listeners.filter((l) => l !== listener);
        }
      }
    }, [])


    if (!visible) return null;

    let description = <>
    LMQL is a query language for large language models. Explore the examples below to get started.
    <LinkBox>
      <a className="button" target="_blank" rel="noreferrer" href="https://docs.lmql.ai">Documentation</a>
      <a className="button" target="_blank" rel="noreferrer" href="https://lmql.ai">Overview</a>
    </LinkBox>
    </>

    if (configuration.NEXT_MODE) {
      description = <>This is the preview channel of LMQL. It contains the latest features, but may be unstable. If you are looking for the stable version, please visit <a href="https://lmql.ai/playground">the stable Playground IDE</a>.</>
    }

    return <PromptPopup>
        <div className="click-handler" onClick={() => ExploreState.setVisibility(false)}/>
        <ExploreDialog>
          <h1 key="welcome">
            <img src="/lmql.svg" alt="LMQL Logo"/>  
            Welcome To LMQL
          </h1>
          <Description>{description}</Description>
          <span className="close" onClick={() => ExploreState.setVisibility(false)}>
            &times;
          </span>
          {exploreQueries.map(c => 
            <div className={c.highlight ? "highlight" : ""} key={c.category + "-container"}>
            <h2 key={c.category}>{c.category}</h2>
            {c.highlight && <span class="sidenote">
              <a href="https://github.com/eth-sri/lmql/issues" target="_blank" rel="noreferrer" title="Please report any issue you find with Preview features to help us improve LMQL."> Report Issues</a>
            </span>}
            <div key={c.category + "-div"}>
            {c.queries.map((q,i) => <Tile key={c.category + "-" + i} onClick={() => onClickTile(q)}>
              {/* {q.state && <div className="badge">PRECOMPUTED</div>} */}
              <BasicHighlighted code={q.code}/>
              <h3>{q.name}</h3>
              <p>{q.description}</p>
            </Tile>)}
            </div>
            </div>
          )}
          {!configuration.NEXT_MODE && <>
          <div>
          <h2 key="read-paper">Read More</h2>
          <CiteBox key="cite">
          Beurer-Kellner, Luca, Marc Fischer, and Martin Vechev. "Prompting Is Programming: A Query Language For Large Language Models." 
          <a target="_blank" rel="noreferrer" href="https://arxiv.org/pdf/2212.06094">arXiv preprint arXiv:2212.06094</a> (2022).
          </CiteBox>
          <br/>
          <PoweredBy>
            <div>LMQL {BUILD_INFO.info().commit}</div>
            <div>
            {(configuration.BROWSER_MODE && !isLocalMode()) && <span> In-Browser, Made with ❤️ + <a href="https://pyodide.org" target="_blank" rel="noreferrer">Pyodide</a> + <a href="https://webassembly.org/" target="_blank" rel="noreferrer">WebAssembly</a></span>}
              {BUILD_INFO.info().date != "-" ? <>
                <br/>
                Build on {BUILD_INFO.info().date}
              </> : null}
            </div>
          </PoweredBy>
          </div>
          </>}
        </ExploreDialog>
    </PromptPopup>
}