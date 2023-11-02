"""
Instance node merging strategies.
"""
from .nodes import InstanceNode, AggregatedInstanceNode
from typing import List
import re
from .runtime import defer_call

class ByValue:
    """
    Merges query result nodes by their exact value.
    """
    def __init__(self, score='mean'):
        self.score = score
        self.none_counts = 0

    def value_normalizer(self, instance: InstanceNode):
        if instance.dangling:
            return id(instance)
        return str(instance.result)

    def _normalize(self, instance: InstanceNode):
        if instance.result is None or instance.dangling:
            i = self.none_counts
            self.none_counts += 1
            return f"{i}"
        return self.value_normalizer(instance)

    def merge(self, instances: List[InstanceNode]):
        instances = AggregatedInstanceNode.flattend(instances)
        buckets = {}

        for i in instances:
            buckets.setdefault(self._normalize(i), []).append(i)
        return [self.merge_group(v) for v in buckets.values()]

    def merge_group(self, equivalent_instances: List[InstanceNode]):
        if len(equivalent_instances) == 1:
            return equivalent_instances[0]
        result = self.value_normalizer(equivalent_instances[0])
        return AggregatedInstanceNode.from_instances(result, equivalent_instances, scoring=self.score)
    
class ByIntValue(ByValue):
    """
    Merges query result nodes by their exact value, but converts them to integers first.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def value_normalizer(self, instance: InstanceNode):
        # use first consecutive digits allowing for , and - also
        return int(re.search(r"[-,\d]+", str(instance.result)).group(0).replace(",", ""))