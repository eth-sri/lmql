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

        self.merging_strategy = None

        self.instances = []

        self.num_calls = 0

    def merge_instances(self):
        if self.merging_strategy is None:
            return
        self.instances = self.merging_strategy.merge(self.instances)

    def add_instance(self, node):
        self.instances.append(node)

    def __repr__(self):
        return "QueryNode(" + self.name + ")"

class InstanceNode:
    """
    An instance node represents the result of a query function with the specified inputs 
    (instance nodes of predecessor queries used to produce this result).
    """
    def __init__(self, result, predecessors, score=1.0):
        self.result = result
        self.predecessors: List[InstanceNode] = predecessors
        self.score = score
        
        # identifier for this result's class (e.g. should be the same for equivalent/aggregated results)
        self.value_class = str(result)

    def __prompt__(self):
        return str(self.result)
    
    def __repr__(self):
        return f"<InstanceNode {self.value_class} {str([self.result])[1:-1]} score={self.score}>"

class AggregatedInstanceNode(InstanceNode):
    def __init__(self, result, children, score):
        predecessors = []
        for c in children:
            predecessors.extend(set(c.predecessors))
        super().__init__(result, predecessors)
        
        self.score = score
        self.children = children
    
    def __repr__(self):
        return f"<AggregatedInstanceNode {len(self.children)} {self.value_class} {str([self.result])[1:-1]} score={self.score}>"

    @classmethod
    def from_instances(cls, result, instances, scoring='mean'):
        if len(instances) == 1:
            return instances[0]
        
        score = 1.0

        if scoring == 'mean':
            score = sum([i.score for i in instances]) / len(instances)
        elif scoring == 'max':
            score = max([i.score for i in instances])
        elif scoring == 'min':
            score = min([i.score for i in instances])
        elif scoring == 'sum':
            score = sum([i.score for i in instances])
        else:
            raise ValueError(f"Unknown score aggregation method '{scoring}'")

        return cls(result, instances, score)
    
    @staticmethod
    def flattend(instances: List[InstanceNode]):
        result = []
        for i in instances:
            if type(i) is AggregatedInstanceNode:
                result.extend(AggregatedInstanceNode.flattend(i.children))
            else:
                result.append(i)
        return result

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
