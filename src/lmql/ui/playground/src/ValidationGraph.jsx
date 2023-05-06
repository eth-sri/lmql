import { useState } from "react";
import React from "react";
import cytoscape from "cytoscape"
import dagre from 'cytoscape-dagre';

import styled from "styled-components";
import { DataListView } from "./DataListView";

cytoscape.use( dagre );

const GraphContainer = styled.div`
  flex: 1;
  display: flex;

  .graph {
    flex: 1;
  }

  .info-view {
    position: absolute;
    font-family: monospace;
    top: -22pt;
    right: 4pt;
    border-radius: 4pt;
    width: 200pt;
    z-index: 999;
    background-color: #1e1e1e;
    border: 0.5pt solid #7d7c7c;
    padding: 5pt;

    &.hidden {
      display: none;
    }
  }
`

function initCytoscape(element) {
    const cy = cytoscape({
      container: element,

      boxSelectionEnabled: false,
      autounselectify: true,

      style: [
        {
          selector: 'node',
          style: {
            // light gray
            'background-color': 'data(color)',
            "shape": "round-rectangle",
            // size
            'width': 80,
            'height': 40,
            "label": "data(label)",
            "font-size": "8px",
            "text-valign": "center",
            "text-halign": "center",
            "color": "#ffffff",
          }
        },
        {
          selector: 'node[is_token=1]',
          style: {
            'label': 'data(token)',
            'background-color': '#f5f5f5',
            'border-color': '#b0b0b0',
            'border-width': '1px',
            'padding': '2px',
            'font-size': '14px',
            'shape': 'rectangle',
            'width': 50,
            'height': 30,
          }
        },
        {
          selector: 'node[is_true]',
          style: {
            'border-color': 'green',
            'border-width': '2px',
            // light green
            'background-color': '#e0ffd0',
          },
        },
        {
          selector: 'node[is_false]',
          style: {
            'border-color': 'red',
            'border-width': '2px',
            // light red
            'background-color': '#ffd0d0',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],

      elements: {}
    });
    // layout(cy);
    cy.fit();
    return cy
};

function InfoView(props) {
    if (!props.node) {
        return <div className="info-view hidden"></div>
    }

    let data = props.node;
    let repr = data.repr

    let [value, final] = data.result
    let result_str = `${final}(${JSON.stringify(value)})`

    return <DataListView className="info-view">
      <table>
        <tbody>
          <tr>
            <td colSpan="2">
              {repr}
            </td>
          </tr>
          <tr>
            <td><h4>Value</h4></td>
            <td className="value">{result_str}</td>
          </tr>
          <tr>
            <td><h4>Follow Map</h4></td>
            <td className="value">{`${data.follow_map.replace("\n", "[NEWLINE]")}`}</td>
          </tr>
        </tbody>
      </table>
    </DataListView>
}

export function ValidationGraph(props) {
    const graphElementRef = React.useRef();
    const cyRef = React.useRef(null);
    const [activeNode, setActiveNode] = useState(null);

    React.useEffect(() => {
        const cy = initCytoscape(graphElementRef.current)
        cyRef.current = cy

        cy.on("click", e => {
            if (e.target && e.target.isNode && e.target.isNode()) {
                setActiveNode(e.target.data())
            } else {
                setActiveNode(null)
            }
        })
    }, [graphElementRef])

    React.useEffect(() => {
        let cy = cyRef.current

        if (cy) {
              setActiveNode(null)
              cy.nodes().remove()
              cy.edges().remove()

              if (!props.graph || props.graph == "None") return;

              props.graph.nodes.forEach(n => {
                  let label = n.data.label;
                  n.data.original_label = label

                  // check and remove prefix <class 'lmql.ops.ops.Lt'>
                  if (label.startsWith("<class 'lmql.ops.ops.")) {
                      label = label.substring("<class 'lmql.ops.ops.".length)
                      label = label.substring(0, label.length - 2)
                  }
                  
                  // derive value and finalness
                  let [value, final] = n.data.result
                  let result_str = `${final}(${value})`
                  n.data.label = label + " " + result_str.substring(0, 12) + (result_str.length > 12 ? "..." : "")
                  
                  // derive color
                  if (final == "fin" && value == false) {
                      n.data.color = "rgb(113, 42, 42)"
                  } else if (value == false) {
                      n.data.color = "rgb(119, 90, 79)"
                  } else if (final == "fin" && value == true) {
                      n.data.color = "rgb(38, 87, 38)"
                  } else if (value == true) {
                      n.data.color = "rgb(58, 88, 58)"
                  } else if (final == "stopped") {
                      n.data.color = "rgb(134, 79, 142)"
                  } else {
                      n.data.color = "rgb(64, 61, 61)"
                  }
                  cy.add({group: "nodes", ...n})
              })
              props.graph.edges.forEach(e => {
                  cy.add({group: "edges", ...e})
              })

              cy.layout({ name: 'dagre'}).run()
              cy.fit();
        }
    }, [props.graph])

    let style = props.style
    return <GraphContainer style={style} className="validation-graph">
        <InfoView node={activeNode}/>
        <div className="graph" ref={graphElementRef}></div>
    </GraphContainer>
}
