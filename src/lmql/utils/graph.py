import io

import pydot
import os

from lmql.ops.ops import Node

def show(pydot_graph):
    # png_str = pydot_graph.create_png(prog=['dot','-Gsize=70,70!'])

    # # treat the DOT output as an image file
    # sio = io.BytesIO()
    # sio.write(png_str)
    # sio.seek(0)
    # img = mpimg.imread(sio)

    # # plot the image
    # imgplot = plt.imshow(img, aspect='equal')
    # plt.show()

    pydot_graph.write_png("out.png", prog=['dot','-Gsize=70,70!'])
    pydot_graph.write_dot('test.dot')
    # os.system("open out.png")

class GraphWriter:
    def __init__(self, name=None, type=None, extra_data_provider=None):
        self.graph = pydot.Dot(name if name is not None else "graphwriter_graph", graph_type='graph')
        
        if type is not None: self.graph.set_type(type)
        
        self.node_names = {}
        self.name_counter = 0 

        self.extra_data_provider = extra_data_provider

    def write(self, obj, info=None):
        if hasattr(obj, "to_graph"):
            obj.to_graph(self)
            return True
        elif hasattr(obj, "__dataclass_fields__"):
            self.node(obj, label=str(type(obj)))
            for f in obj.__dataclass_fields__:
                vs = obj.__dict__[f]
                if type(vs) is not list: vs = [vs]
                for v in vs:
                    if self.write(v, f):
                        self.edge(obj, v)
            return True
        elif isinstance(obj, Node):
            self.node(obj, label=str(type(obj)))
            for i, p in enumerate(obj.predecessors):
                if self.write(p, str(i)):
                    self.edge(p, obj)
            return True
        elif type(obj) is str:
            return False
        elif type(obj) is int:
            return False
        elif type(obj) is bool:
            return False
        elif type(obj) is list:
            return False
        elif type(obj) is set:
            return False
        elif obj is None:
            return False
        elif callable(obj):
            return False
        else:
            if hasattr(obj, "getText"):
                print(obj.getText())

            print("warning: not a support object type to be written to a graph: {} {} {}".format(type(obj), obj, info if info is not None else ""))
            return False

    def node(self, obj, label=None, **kwargs):
        if label is None: 
            if hasattr(obj, "__nodelabel__"):
                label = obj.__nodelabel__()
            else:
                label = str(type(obj).__name__)

        cyto_data = {}
        if hasattr(obj, "__cyto_data__"):
            cyto_data = obj.__cyto_data__()
        elif self.extra_data_provider is not None:
            cyto_data = self.extra_data_provider(obj)

        if obj in self.node_names:
            name = self.node_names[obj]
            n = self.graph.get_node(name)
            if label is not None: 
                n[0].set_label(label)
            return n[0]
        else:
            name = f"n{self.name_counter}"
            self.name_counter += 1
            self.node_names[obj] = name

        n = pydot.Node(name, label=label, shape="box", **kwargs, cyto_data=cyto_data)
        self.graph.add_node(n)

        return name

    def edge(self, src, dst):
        n1 = self.node(src)
        n2 = self.node(dst)

        self.graph.add_edge(pydot.Edge(n1, n2))

    def show(self):
        show(self.graph)

class CytoscapeNode:
    def __init__(self, node, graph):
        self.node = node
        self.graph = graph

    def set_label(self, l):
        # print("update label", l)
        self.graph.nodes[self.node]["data"]["label"] = l

class CytoscapeGraph:
    def __init__(self) -> None:
        self.nodes = {}
        self.edges = []

    def to_json(self, return_dict=False):
        import json

        d = {
            "nodes": list(self.nodes.values()),
            "edges": self.edges
        }

        if return_dict: return d
        else: return json.dumps(d)

    def add_node(self, node_data, label=None):
        node = node_data.obj_dict["name"]
        if label is None and "label" in node_data.obj_dict["attributes"]:
            label = node_data.obj_dict["attributes"]["label"]
        if label is None and node in self.nodes.keys():
            label = self.nodes[node]["data"]["label"]

        self.nodes[node] = {
            "data": { 
                "id": node,
                "label": label,
                "is_token": 1 if "SequenceOp" in label else 0
            }
        }

        if "cyto_data" in node_data.obj_dict["attributes"]:
            self.nodes[node]["data"].update(node_data.obj_dict["attributes"]["cyto_data"])

    def get_node(self, node):
        return [CytoscapeNode(node, self)] if node in self.nodes else []

    def add_edge(self, edge):
        src, dst = edge.obj_dict["points"]
        if type(src) is CytoscapeNode: src = src.node
        if type(dst) is CytoscapeNode: dst = dst.node

        self.edges.append({ "data": { "source": src, "target": dst } })


class CytoscapeGraphWriter(GraphWriter):
    def __init__(self, name=None, type=None, extra_data_provider=None):
        super().__init__(name, type, extra_data_provider=extra_data_provider)
        self.graph = CytoscapeGraph()