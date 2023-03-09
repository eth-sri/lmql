import React, { useEffect, useRef, useState } from "react";
import styled from "styled-components";
import {queries} from "./queries";
import exploreIcon from "./explore.svg"
import { persistedState, trackingState } from "./State";

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
  padding: 10pt;
  margin: auto;
  max-width: 500pt;
  max-height: 500pt;
  overflow: auto;
  color: black;

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

  label {
    font-size: 10pt;
    position: relative;
    top: 8pt;
    left: 2pt;
  }
`

const ExploreDialog = styled(Dialog)`
  width: 550pt;
  height: 550pt;
  max-height: 100vh;
  max-width: 100vh;
  overflow-y: auto;
  position: relative;
  padding: 20pt;

  @media (max-width: 550pt) {
    width: calc(100vw - 20pt);
    height: calc(100vh - 20pt);
    max-height: 100vh;
    max-width: 100vh;
    overflow-y: auto;
    position: relative;
    padding: 10pt;
  }

  /* very light white to grey grdient */
  background: linear-gradient(180deg, #ffffff 0%, #e4e2e2 100%);

  >div {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
  }

  p {
    text-align: justify;
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
    color: #373737;
  }

  h3 {
    font-size: 12pt;
    color: #373737;
    margin: 0;
    z-index: 999;
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
  background-color: #1e1e1e;
  border-radius: 4pt;
  padding: 10pt;
  margin: 10pt;
  margin-left: 0pt;
  margin-top: 0pt;
  cursor: pointer;
  transition: 0.1s;
  height: 80pt;
  width: 100pt;
  border: 2pt solid white;
  opacity: 0.9;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-end;

  :hover {
    transform: scale(1.05);
    opacity: 1.0;
  }

  h3 {
    color: #e9e8e8;
  }

  code {
    opacity: 0.3;
  }

  p {
    color: white;
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
    visible: false,
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
  color: white;

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
    background: linear-gradient(180deg, transparent 0%, #1e1e1e 100%);
  }
`

const TypingContainer = styled.span`
  .cursor {
    animation: blink 2s linear infinite;
    transform: scale(2.2);
    transform-origin: top middle;
    font-size: 25pt;
    height: 15pt;
    background-color: black;
    width: 1pt;
    position: relative;
    left: 3pt;
    content: " ";
    overflow: hidden;
    display: inline-block;
  }

  @keyframes blink {
    0% {
      opacity: 0;
    }
    50% {
      opacity: 1;
    }
    100% {
      opacity: 0;
    }
  }
`


function TypedText() {
  let [text, setText] = useState("Welcome To LMQL");
  let [index, setIndex] = useState(window.textWasTyped ? text.length : 0);
  let [speed, setSpeed] = useState(50);
  let [isTyping, setIsTyping] = useState(!window.textWasTyped);

  useEffect(() => {
    if (!isTyping) return;
    
    if (index < text.length) {
      setTimeout(() => {
        setIndex(index + 1);
      }, speed);
    } else {
      setIsTyping(false);
      window.textWasTyped = true;
    }
  })

  function type(text, speed) {
    setText(text);
    setIndex(0);
    setSpeed(speed);
    setIsTyping(true);
  }

  return <TypingContainer>
    {text.substring(0, index)}
    <span className="cursor"></span>
  </TypingContainer>
}

function BasicHighlighted(props) {
  const s = props.code;

  const keywords = ["argmax", "where", "from", "and", "or", "not", "sample", "beam_search"];
  // split into words (also split on ()\t\n)
  const words = s.split(/(\s+|[\(\)\t])/g);
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
  font-size: 12pt;
  color: #696969;
`

const CiteBox = styled.code`
  display: block;
  background-color: #dfdede;
  padding: 4pt;
  border-radius: 4pt;
`

let didLoadAnchor = false;

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

    useEffect(() => {
        // register listeners
        ExploreState.listeners.push(setVisible);

        // check if first visit
        const editorContents = window.localStorage.getItem("lmql-editor-contents");
        if (editorContents === null || (typeof editorContents === "string" && editorContents.trim().length === 0)) {
          ExploreState.setVisibility(true);
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

    if (!visible) return null;

    return <PromptPopup>
        <div className="click-handler" onClick={() => ExploreState.setVisibility(false)}/>
        <ExploreDialog>
          <h1 key="welcome">
            <img src="/lmql.svg" alt="LMQL Logo"/>  
            <TypedText text="Welcome To LMQL" speed={20}/>
          </h1>
          <Description>
            LMQL is a query language for large language models. This playground allows you to explore LMQL's capabilities. To get started, choose one of the example queries below, demonstrating <i>constrained model use</i>, <i>control-flow guided generation</i>, and tool-augmented LLMs.
          </Description>
          <a className="close" onClick={() => ExploreState.setVisibility(false)}>
            &times;
          </a>
          {queries.map(c => 
            <>
            <h2 key={c.category} key={c.category}>{c.category}</h2>
            <div key={c.category + "-div"}>
            {c.queries.map((q,i) => <Tile key={c.category + "-" + i} onClick={() => onClickTile(q)}>
              {/* {q.state && <div className="badge">PRECOMPUTED</div>} */}
              <BasicHighlighted code={q.code}/>
              <h3>{q.name}</h3>
              <p>{q.description}</p>
            </Tile>)}
            </div>
            </>
          )}
          <h2 key="read-paper">Read the Paper</h2>
          <CiteBox key="cite">
          Anonymous Authors
          </CiteBox>
        </ExploreDialog>
    </PromptPopup>
}