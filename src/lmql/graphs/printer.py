"""
Prints LMQL inference graphs and their state to a viewer-compatible JSON format.
"""
import json
from .nodes import AggregatedInstanceNode, InstanceNode, QueryNode

class InferenceGraphPrinter:
    def __init__(self):
        self.id_counter = 0

    def to_json(self, graph):
        entries = []
        node_ids = {}
        value_classes = {}

        for n in graph.nodes:
            if id(n) not in node_ids:
                node_ids[id(n)] = f"node{self.id_counter}"
                self.id_counter += 1

            lmql_signature = {
                "lmql": n.query_fct.lmql_code,
                "lmql_inputs": str(n.query_fct.input_keys),
                "lmql_outputs": n.query_fct.output_keys,
                "lmql_dependencies": str(n.query_fct.resolved_query_dependencies())
            }
            
            entries.append({"data": {
                "id": node_ids[id(n)], 
                "label": n.name,
                "composite": True,
                **lmql_signature
            }})

            for i, instance in enumerate(n.instances):
                entries.append(self.instance_json(n, i, instance, lmql_signature, node_ids, value_classes))

        for n in graph.nodes:
            # meta edges
            for edge in n.incoming:
                for d in edge.dependencies:
                    if id(d) in node_ids:
                        entries.append({"data": {
                            "target": node_ids[id(n)],
                            "source": node_ids[id(d)],
                            "meta": True
                        }})

            # instance edges
            for i, instance in enumerate(n.instances):
                for d in instance.predecessors:
                    if id(d) in node_ids:
                        entries.append({"data": {
                            "target": node_ids[id(instance)],
                            "source": node_ids[id(d)]
                        }})

        return json.dumps(entries, indent=4)

    def instance_json(self, n: QueryNode, i: int, instance: InstanceNode, lmql_signature, node_ids, value_classes):
        if id(instance) not in node_ids:
            node_ids[id(instance)] = f"instance{self.id_counter}"
            self.id_counter += 1

        value_class_id = value_classes.get(instance.value_class, len(value_classes) + 1)
        value_classes[instance.value_class] = value_class_id

        aggregate_node_data = []
        if type(instance) is AggregatedInstanceNode:
            for j, child in enumerate(instance.children):
                aggregate_node_data.append(self.instance_json(n, j, child, lmql_signature, 
                                                        node_ids, value_classes))

        return {
            "data": {
                "id": node_ids[id(instance)],
                **lmql_signature,
                "label": n.name.split("(",1)[0] + f"#{i}",
                "result": str(instance.result),
                "parent": node_ids[id(n)],
                "value_class_id": value_class_id,
                "score": instance.score,
                "children": aggregate_node_data,
                "dangling": instance.dangling,
                "resumable": str(instance.resumable)
            }
        }