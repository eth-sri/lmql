"""
Node types for LMQL Graphs.
"""

class QueryNode:
    def __init__(self, name, query_fct):
        self.name = name
        self.query_fct = query_fct
        self.predecessors = []

        self.instances = []

    def add_instance(self, node):
        self.instances.append(node)

    def __repr__(self):
        return "QueryNode(" + self.name + ")"

class InstanceNode:
    def __init__(self, result, predecessors):
        self.result = result
        self.predecessors = predecessors
        
        # identifier for this result's class (e.g. same for equivalent results)
        self.value_class = str(result)

class Edge:
    def __init__(self, dependencies, target):
        self.dependencies = dependencies
        self.target = target
    
    def __repr__(self):
        return f"{self.dependencies} -> {self.target}"
