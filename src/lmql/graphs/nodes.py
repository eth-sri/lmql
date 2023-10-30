"""
Node types for LMQL Graphs.
"""
from typing import List

class QueryNode:
    """
    A query node represents a single LMQL query function with edges to 
    its predecessors queries (i.e. the queries it calls in its body).
    """
    def __init__(self, name, query_fct):
        self.name = name
        self.query_fct = query_fct
        self.incoming: List['QueryEdge'] = []

        self.instances = []

    def add_instance(self, node):
        self.instances.append(node)

    def __repr__(self):
        return "QueryNode(" + self.name + ")"

class InstanceNode:
    """
    An instance node represents the result of a query function with the specified inputs 
    (instance nodes of predecessor queries used to produce this result).
    """
    def __init__(self, result, predecessors):
        self.result = result
        self.predecessors: List[InstanceNode] = predecessors
        
        # identifier for this result's class (e.g. should be the same for equivalent/aggregated results)
        self.value_class = str(result)

class QueryEdge:
    """
    A hyperedge representing one set of dependency query nodes that are enough
    for at least one instantiation of a query function (e.g. in case of branching
    calls a query node may have more than one set of dependencies).
    """
    def __init__(self, dependencies, target):
        self.dependencies = dependencies
        self.target: QueryNode = target
    
    def __repr__(self):
        return f"{self.dependencies} -> {self.target}"
