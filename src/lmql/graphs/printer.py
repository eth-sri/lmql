"""
Prints LMQL inference graphs and their state to a viewer-compatible JSON format.
"""
import json

def to_json(graph):
    entries = []
    id_counter = 0
    node_ids = {}
    value_classes = {}

    for n in graph.nodes:
        if id(n) not in node_ids:
            node_ids[id(n)] = f"node{id_counter}"
            id_counter += 1

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
            if id(instance) not in node_ids:
                node_ids[id(instance)] = f"instance{id_counter}"
                id_counter += 1
            
            value_class_id = value_classes.get(instance.value_class, len(value_classes) + 1)
            value_classes[instance.value_class] = value_class_id

            entries.append({"data": {
                "id": node_ids[id(instance)],
                **lmql_signature,
                "label": n.name + f"#{i}",
                "result": str(instance.result),
                "parent": node_ids[id(n)],
                "value_class_id": value_class_id
            }})

    for n in graph.nodes:
        # meta edges
        for edge in n.predecessors:
            for d in edge.dependencies:
                entries.append({"data": {
                    "target": node_ids[id(n)],
                    "source": node_ids[id(d)],
                    "meta": True
                }})

        # instance edges
        for i, instance in enumerate(n.instances):
            for d in instance.predecessors:
                entries.append({"data": {
                    "target": node_ids[id(instance)],
                    "source": node_ids[id(d)]
                }})

    return json.dumps(entries, indent=4)