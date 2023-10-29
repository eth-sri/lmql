import inspect
from itertools import product

class QueryNode:
    def __init__(self, name, query_fct):
        self.name = name
        self.query_fct = query_fct
        self.predecessors = []

    def __repr__(self):
        return self.name

class Edge:
    def __init__(self, dependencies, target):
        self.dependencies = dependencies
        self.target = target
    
    def __repr__(self):
        return f"{self.dependencies} -> {self.target}"

def build_graph(query_fct, graph: set):
    query_node = QueryNode(query_fct.name, query_fct)
    factored_dependencies = query_fct.resolved_query_dependencies()
    if len(factored_dependencies) == 0:
        graph.add(query_node)
        return query_node
    
    factored_dependencies = [[dep] if type(dep) is not list else dep for dep in factored_dependencies]
    for deps in product(*factored_dependencies):
        edge = Edge([build_graph(pred, graph=graph) for pred in deps], target=query_node)
        graph.add(edge)
        query_node.predecessors.append(edge)
    graph.add(query_node)
    return query_node

def infer(fct, *args, **kwargs):
    qfct = fct.__lmql_query_function__
    graph = set()
    build_graph(qfct, graph=graph)
    print(graph)