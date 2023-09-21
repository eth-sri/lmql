import React, { useEffect, useRef, useState } from "react";
import { LMQLProcess } from './Configuration';
import { persistedState } from "./State"

import cytoscape from "cytoscape"

function layoutDecoderGraph(cy) {
    const rootNodes = cy.nodes().filter(n => n.indegree() == 0)
    let columnItems = new Map()
    let cellWidth = 90
    let cellHeight = 50

    cy.elements().depthFirstSearch({
        roots: rootNodes,
        visit: (node, edge, previous, i, depth) => {
            let column = columnItems.get(depth)
            let sortData = [node.data("seqlogprob"), node.data("pool"), node.data("seq_id")]

            if (!columnItems.has(depth)) {
                column = [[node.id(), sortData]]
                columnItems.set(depth, column)
            } else {
                column.push([node.id(), sortData])
                columnItems.set(depth, column)
            }
        },
        directed: true
    });

    // set node width based on label
    cy.nodes().forEach(n => {
        // skip compound
        if (n.hasClass("compound")) return
        // set label to label (seqlogprob)
        let seqlogprob = n.data("seqlogprob")
        // if seqlogprob is a number
        if (typeof seqlogprob === "number") {
            seqlogprob = seqlogprob.toFixed(2)
        } else if (typeof seqlogprob === "string") {
            // parse inf, -inf
            if (seqlogprob == "inf") {
                seqlogprob = Infinity
            } else if (seqlogprob == "-inf") {
                seqlogprob = -Infinity
            } else {
                seqlogprob = -9999
            }
        } else {
            seqlogprob = -9999
        }
        let label = n.data("label") + "\n(" + seqlogprob + ")"
        n.data("label", label)

        let width = label.length * 4
        if (n.data("root")) {
            width = 20
        }
        n.style("width", Math.max(width, 30))
    })

    Array.from(columnItems.keys()).forEach(k => {
        let column = columnItems.get(k)
        
        function compare(a,b) {
            let [seqlogprob, pool, seq_id] = a[1]
            let [seqlogprob2, pool2, seq_id2] = b[1]
            // sort by pool (str) first than by seqlogprob
            // use string comparison on pool, null is always last
            if (pool == null) {
                if (pool2 == null) {
                    // compare by seqlogprob
                    if (seqlogprob > seqlogprob2) {
                        return -1
                    } else if (seqlogprob < seqlogprob2) {
                        return 1
                    } else {
                        // compare by seq_id
                        return seq_id - seq_id2
                    }
                } else {
                    return 1
                }
            } else if (pool2 == null) {
                return -1
            } else if (pool < pool2) {
                return -1
            } else if (pool > pool2) {
                return 1
            } else { // pool == pool2
                if (seqlogprob > seqlogprob2) {
                    return -1
                } else if (seqlogprob < seqlogprob2) {
                    return 1
                } else {
                    return 0
                }
            }
        }

        column.sort(compare)
        // turn into map to index
        column = new Map(column.map((v,i) => [v[0], i]))
        columnItems.set(k, column)
    })

    let compoundNodes = new Set()

    cy.nodes().forEach(n => {
        let pool = n.data("pool")
        if (compoundNodes.has(pool)) {
            return
        }
        if (!pool) {
            return
        }

        let id = "compound_" + pool

        if (cy.getElementById(id).length > 0) {
            return
        }

        let compoundNode = cy.add({
            group: "nodes",
            data: {
                id: id,
                label: pool,
            }
        })
        compoundNode.addClass("compound")
        compoundNodes.add(pool)
    })

    let maxDepth = Math.max(...Array.from(columnItems.keys()))

    // set .stopped for all nodes without outgoing edges
    cy.elements().depthFirstSearch({
        roots: rootNodes,
        visit: (n, edge, previous, i, depth) => {
            if (depth >= maxDepth) return;
            // no outgoers and not compound node
            if (n.outgoers().length == 0 && !n.hasClass("compound")) {
                n.addClass("stopped")
            }
        },
        directed: true
    });

    // set position, compound and layouted properties
    cy.elements().depthFirstSearch({
        roots: rootNodes,
        visit: (node, edge, previous, i, depth) => {
            if (node.data("layouted")) return;
            if (node.hasClass("compound")) return;

            let column = columnItems.get(depth).get(node.id())
            node.position({x: depth * cellWidth, y: cellHeight * column})
            node.data("layouted", true)

            let pool = node.data("pool")
            if (pool) {
                node.move({parent: "compound_" + pool})
            }
        },
        directed: true
    });

    // determine most recent most likely node
    let mostLikelyMostRecentNode = null;
    let mostLikelyDepth = 0;
    
    cy.elements().depthFirstSearch({
        roots: rootNodes,
        visit: (node, edge, previous, i, depth) => {
            if (node.hasClass("compound")) return;
            if (node.data("_noUserData")) return;

            // console.log("data", node.data())
            depth = parseInt(node.data("seq_id").substr(2))

            if (depth >= mostLikelyDepth) {
                if (depth > mostLikelyDepth) {
                    mostLikelyMostRecentNode = null
                }
                mostLikelyDepth = depth
                if (mostLikelyMostRecentNode) {
                    if (mostLikelyMostRecentNode.data("seqlogprob") < node.data("seqlogprob")) {
                        mostLikelyMostRecentNode = node
                    }
                } else {
                    mostLikelyMostRecentNode = node
                }
            }
        },
        directed: true
    });

    return mostLikelyMostRecentNode
}

function initDecoderGraphCy(element) {
    return cytoscape({
        container: element,
        maxZoom: 2.0,
        boxSelectionEnabled: false,
        autounselectify: true,
        // dpi scale
        pixelRatio: 3,

        style: [
            {
            selector: 'node',
            style: {
                // very light gray
                'background-color': '#f5f5f5',
                'label': 'data(label)',
                'shape': 'roundrectangle',
                'text-valign': 'center',
                'text-halign': 'center',
                'text-wrap': 'wrap',
                'text-max-width': '100px',
                'text-justification': 'center',
                'color': '#505050',
                'font-size': '10px',
                'border-color': '#e2e2e2',
                'border-width': '1px',
                'font-family': 'monospace',
            }
            },
            {
                selector: 'node[_isRoot]',
                style: {
                    'label': '●',
                }
                },
            // node with data head.valid == false
            {
                selector: 'node[_finfalse]',
                style: {
                    'background-color': '#e86868',
                    'background-opacity': 0.5,
                    'border-color': '#e2e2e2'
                },
            },
            {
            selector: 'node.stopped',
            style: {
                'background-color': 'white',
                'background-opacity': 0.0,
                'border-color': 'white',
                'border-width': '0px',
                'color': '#d0caca',
            }
            },
            {
                selector: 'node.active[deterministic]',
                style: {
                    'background-color': '#334768',
                    'background-opacity': 1.0,
                    'color': 'white',
                    'border-color': 'grey',
                    'border-width': '0px',
                }
            },
            // node with data.deterministic
            {
                selector: 'node[deterministic]',
                style: {
                    // light blue
                    'background-color': '#9dbaea',
                    'background-opacity': 1.0,
                    'color': 'white',
                    'border-color': 'grey',
                    'border-width': '0px',
                }
            },
            {
                selector: 'node[_isDone]',
                style: {
                    // light blue
                    'background-color': 'rgb(146, 185, 146)',
                    'background-opacity': 1.0,
                    'color': 'white',
                    'border-color': 'green',
                    'border-width': '0px',
                }
            },
            {
                selector: 'node[_noUserData]',
                style: {
                    // light blue
                    'background-color': 'rgb(249, 209, 248)',
                    'background-opacity': 0.7,
                    'color': 'white',
                    'border-color': 'red',
                    'border-width': '0px',
                    'opacity': 0.4
                }
            },
            {
                selector: 'node.inactive',
                style: {
                    'opacity': 0.5
                }
            },
            //   active nodes
            {
                selector: 'node.active',
                style: {
                    'background-color': '#337ab7',
                    'background-opacity': 1.0,
                    'color': 'white',
                    'opacity': 1.0
                }
            },
            {
                selector: 'node.active.downstream',
                style: {
                    'background-color': '#7d7c7c',
                    'background-opacity': 1.0,
                    'color': 'white',
                }
            },
            {
                selector: 'node.active.lynchpin.downstream',
                style: {
                    'background-color': '#42bd69',
                    'background-opacity': 1.0,
                    'color': 'white',
                }
            },
            //   compound nodes
            {
                selector: 'node.compound, node.compound.active',
                style: {
                    'color': '#d0caca',
                    'shape': 'roundrectangle',
                    // text top center but inside node
                    'text-valign': 'top',
                    'text-halign': 'center',
                    'text-wrap': 'wrap',
                    'font-weight': 'bold',
                    'font-size': '8pt',
                    'background-color': '#b6b4b45e',
                    'background-opacity': 0.3,
                    'border-color': '#e2e2e2',
                    'border-width': '1px',
                    'padding': '2',
                    'text-margin-y': '-2',
                }
            },
            {
            selector: 'edge',
            style: {
                'width': 2,
                'target-arrow-shape': 'triangle',
                'line-color': '#9dbaea',
                'target-arrow-color': '#9dbaea',
                "curve-style": "bezier",
            }
            },
            {
                selector: 'edge.inactive',
                style: {
                    'line-color': '#337ab7',
                    'target-arrow-color': '#337ab7',
                    'width': 4,
                    'opacity': 0.5
                }
            },
            {
            selector: 'edge.active',
            style: {
                'line-color': 'white',
                'target-arrow-color': 'white',
                'width': 4,
                'opacity': 1.0
            }
            },
        ],

        elements: {
            nodes: [],
            edges: []
        }
    });
}

function highlightDownstreamFrom(node) {
    node.addClass("active")
    node.addClass("downstream")
    node.outgoers().forEach(n => highlightDownstreamFrom(n))
}

function highlightPathTo(root, target) {
    target.addClass("lynchpin")
    highlightDownstreamFrom(target)
    let predecessor = target.incomers()[0]
    while(predecessor) {
        predecessor.addClass("active")
        predecessor = predecessor.source()
        predecessor.addClass("active")
        predecessor = predecessor.incomers()[0]
    }
}

export function DecoderGraph(props) {
    const graphElementRef = React.useRef();

    const derivedNodeFeatures = props.derivedNodeFeatures || (() => {})

    const [cyData, setCyData] = useState(null);
    const [rawGraphData, setRawGraphData] = useState(null);
    const cyRef = useRef(null)

    props.fitTrigger && props.fitTrigger.addTriggerListener(() => cyRef.current.fit())

    const reset = () => {
        if (cyRef.current) {
            cyRef.current.nodes().remove()
            cyRef.current.edges().remove()
        } else {
            console.log("no cy to reset", cyRef.current, "is cy")
        }
    }

    // listen for changes to persisted graph
    const onPersistedGraphChange = React.useCallback((s) => {
        if (rawGraphData == s) {
            return
        }
        reset()
        setCyData(JSON.parse(s))
        setTimeout(() => cyRef.current.fit(), 0)
    }, [])

    React.useEffect(() => {
        // restore previous graph data
        let graphData = persistedState.getItem("decoder-graph") || null
        if (graphData) {
            let graph = JSON.parse(graphData);
            setCyData(graph)
        }

        persistedState.on("decoder-graph", onPersistedGraphChange)

        return () => {
            // remove listener
            persistedState.remove("decoder-graph", onPersistedGraphChange)
        };
    }, []);
    
    React.useEffect(() => {
        const cy = initDecoderGraphCy(graphElementRef.current)
        cyRef.current = cy
            
        // when clicking a node, highlight all paths to root
        function onSelectNode(evt) {
            let node = evt.target
            let nodes = [node]
            
            // for compound nodes, select all children
            if (node.isParent()) {
                nodes = node.descendants()
            }

            let rootNodes = cy.nodes().filter(n => n.indegree() == 0)
            // remove active otherwise
            if (!evt.originalEvent.shiftKey) {
                cy.elements().removeClass("active").removeClass("downstream").removeClass("lynchpin").removeClass("inactive")
            }

            nodes.forEach((node, i) => {
                cy.elements().addClass("inactive")
                highlightPathTo(rootNodes, node)
                
                if (props.onSelectNode) {
                    props.onSelectNode(node, evt.originalEvent.shiftKey || (i > 0 && nodes.length > 1))
                }
            })
            
            node.addClass("active")
        }
        cy.on('tap', 'node', onSelectNode)

        // also allow parent component to set selected node
        if (props.selectedNodeTrigger) {
            props.selectedNodeTrigger.addTriggerListener((node) => {
                onSelectNode({target: node, originalEvent: {shiftKey: false}})
            })
        }

        // tap anywhere clear active
        cy.on('tap', function(evt){
            if (evt.target === cy) {
                cy.elements().removeClass("active").removeClass("downstream").removeClass("lynchpin").removeClass("inactive")
                if (props.onSelectNode) {
                    props.onSelectNode(null)
                }
            }
        })
    }, [graphElementRef])

    React.useEffect(() => {
        const cy = cyRef.current
        if (cy) {
            if (cyData) {
                // collect unique edges
                const uniqueEdges = new Map()
                cyData.edges.forEach(e => {
                    let edge = uniqueEdges.get(e[0])
                    if (!edge) {
                        edge = new Set()
                        uniqueEdges.set(e[0], edge)
                    }
                    edge.add(e[1])
                })

                function strLabel(label) {
                    // unpack arrays
                    if (Array.isArray(label)) {
                        return label.map(strLabel).join(", ")
                    }
                    if (label.startsWith("bytes:")) {
                        label = label.substring(6)
                        return label
                    }
                    if (label === "") {
                        // epsilon
                        return "\u03b5"
                    }
                    if (!label) {
                        return ""
                    }
                    if (label == "") {
                        // epsilon
                        return "\u03b5"
                    }
                    try {
                        label = label.replace(/ /g, "\u23b5")
                        if (label.length > 20) {
                            return label.substring(0, 20) + "..."
                        }
                        return label
                    } catch (e) {
                        console.error("error with label", label)
                        return "<error>"
                    }
                }

                // transform nodes and edges
                cyData.nodes.forEach(node => {
                    let n = {
                        data: {
                            ...node,
                            id: node.id,
                            // replace space by utf-8 0x23b5
                            label: strLabel(node.text[0])
                        }
                    };
                    const derived = derivedNodeFeatures(n.data);
                    Object.keys(derived).filter(k => derived[k]).forEach(k => n.data[k] = derived[k]);

                    // get node with id node.id
                    let existingNode = cy.getElementById(node.id)
                    if (existingNode.length > 0) {
                        let oldPool = existingNode.data("pool")
                        // update node
                        existingNode.data(n.data)
                        if (existingNode.data("pool") != oldPool) {
                            existingNode.data("layouted", false)
                        }
                        // when eager layout is active, always lay out nodes on new data
                        if (props.eagerLayout) existingNode.data("layouted", false)
                    } else {
                        cy.add({group: "nodes", ...n})
                    }
                })
                
                Array.from(uniqueEdges).forEach(([from, tos]) => Array.from(tos).forEach(to => {
                    let existingSource = cy.getElementById(from)
                    let existingTarget = cy.getElementById(to)
                    if (existingSource.edgesTo(existingTarget).length > 0) {
                        // edge already exists
                        return
                    }
                    let e ={
                        data: {
                            source: from,
                            target: to
                        }
                    };
                    try {
                        cy.add({group: "edges", ...e})
                    } catch (e) {
                        console.error("error adding edge", e)
                    }
                }))

                let mostLikely = layoutDecoderGraph(cy)
                
                if (props.onMostLiklyNode) {
                    props.onMostLiklyNode(mostLikely)
                }
            } else {
                cy.nodes().remove()
                cy.edges().remove()
            }
        }
    }, [cyData, cyRef])

    // on mount
    useEffect(() => {
        // conn is RemotePRocessConnection
        const renderer = {
            add_result: (output) => {
                if (output.type == "decoder-graph-state") {
                    setCyData(cyData => {
                        // persist decoder graph in local state
                        let updated = Object.assign({nodes: [], edges: []}, cyData || {})
                        let nodes = {}
                        updated.nodes.forEach(n => nodes[n.id] = n)
                        output.data.nodes.forEach(n => nodes[n.id] = n)
                        updated.nodes = Array.from(Object.values(nodes))
                        
                        updated.edges = Array.from([...updated.edges, ...output.data.edges])
                        
                        // console.log("updating", output.data.nodes.length)

                        const raw = JSON.stringify(updated)
                        setRawGraphData(raw)
                        persistedState.queueSetItem("decoder-graph", raw, onPersistedGraphChange)
                        return updated
                    })
                } else {
                    // nop in this component
                }
            },
            clear_results: () => setCyData(null),
        }
        LMQLProcess.addRenderer(renderer)
        return () => {
            LMQLProcess.remove("render", renderer)
        }
    }, []);

    let style = Object.assign({
        width: "100%",
        height: "100%"
    }, props.style)

    return <div className="graph" style={style} ref={graphElementRef}></div>
}
