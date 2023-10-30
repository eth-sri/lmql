"""
Instance node merging strategies.
"""
from .nodes import InstanceNode, AggregatedInstanceNode
from typing import List

class ByValue:
    """
    Merges query result nodes by their exact value.
    """
    def __init__(self):
        pass

    def merge(self, instances: List[InstanceNode]):
        instances = AggregatedInstanceNode.flattend(instances)
        buckets = {}

        for i in instances:
            buckets.setdefault(i.value_class, []).append(i)
        return [self.merge_group(v) for v in buckets.values()]

    def merge_group(self, equivalent_instances: List[InstanceNode]):
        result = equivalent_instances[0].result
        return AggregatedInstanceNode.from_instances(result, equivalent_instances)