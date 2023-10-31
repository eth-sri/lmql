"""
Instance node merging strategies.
"""
from .nodes import InstanceNode, AggregatedInstanceNode
from typing import List
import re

class ByValue:
    """
    Merges query result nodes by their exact value.
    """
    def __init__(self):
        pass

    def value_normalizer(self, instance: InstanceNode):
        return str(instance.result)

    def merge(self, instances: List[InstanceNode]):
        instances = AggregatedInstanceNode.flattend(instances)
        buckets = {}

        for i in instances:
            buckets.setdefault(self.value_normalizer(i), []).append(i)
        return [self.merge_group(v) for v in buckets.values()]

    def merge_group(self, equivalent_instances: List[InstanceNode]):
        result = self.value_normalizer(equivalent_instances[0])
        return AggregatedInstanceNode.from_instances(result, equivalent_instances)
    
class ByIntValue(ByValue):
    """
    Merges query result nodes by their exact value, but converts them to integers first.
    """
    def __init__(self):
        super().__init__()

    def value_normalizer(self, instance: InstanceNode):
        # use first consecutive digits allowing for , and - also
        return int(re.search(r"[-,\d]+", str(instance.result)).group(0).replace(",", ""))