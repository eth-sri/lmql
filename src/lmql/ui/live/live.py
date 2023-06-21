import os

import sys
sys.path.append("../")
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from livelib import LiveApp, live, add_debugger_output
import json
import numpy as np
import asyncio

class LiveDebuggerOutputWriter:
    def __init__(self, web):
        self.records_graph = True
        self.web = web

    def add_decoder_state(self, graph_dict):
        add_debugger_output("decoder-graph-state", graph_dict)
    
    def report_model_stats(self, **kwargs):
        add_debugger_output("openai-token-count", kwargs)
        
    async def input(self, *args):
        add_debugger_output("stdin-request", {})
        return await LiveApp.ainput(*args, web=self.web)

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        from lmql.utils.graph import CytoscapeGraphWriter
        
        def node_data(op):
            follow_map = "<follow_map output not supported>"

            result = "-"
            if trace is not None and op in trace:
                result = trace[op]

            return {
                "result": result,
                "follow_map": follow_map,
                "repr": repr(op)
            }

        writer = CytoscapeGraphWriter(extra_data_provider=node_data)
        writer.write(where)

        args = ("interpreter-head", {
            "variable": variable,
            "head_index": head,
            "prompt": prompt,
            "mask": str(mask),
            "valid": str(is_valid),
            "final": is_final,
            "num_tokens": num_tokens,
            "program_variables": program_variables.variable_values if program_variables is not None else {},
            "where": writer.graph.to_json()
        })
        add_debugger_output(*args)
        
    def add_compiler_output(self, code): 
        add_debugger_output("compiled-code", {
            "code": code
        })

@live()
async def lmql(code, *args, web=False):
    import lmql
    
    model = None
    if len(args) > 0 and type(args[0]) is dict:
        model = args[0].get("model")
        if model == "automatic": model = None

    if code.startswith("./"):
        with open(code) as f:
            code = f.read()

    output_writer = LiveDebuggerOutputWriter(web=web)

    result = await lmql.run(code, output_writer=output_writer, model=model)

    for r in (result if type(result) is list else [result]):
        if r is None:
            continue

        if type(r) is not lmql.LMQLResult:
            continue
        
        for v in [v for v in r.variables if v.startswith("P(")]:
            distribution = r.variables[v]
            max_prob = max([p for _,p in distribution])
            labels = []
            for value, prob in distribution:
                label = value if prob != max_prob else f"{value} (*)"
                labels.append(label)
            max_length = max([len(str(l)) for l in labels])

            print(v)
            for (value, prob), label in zip(distribution, labels):
                label = label.ljust(max_length)
                print(" - {} {}".format(label, prob))

def replace_inf_nan_with_str(d):
    import math
    for k, v in d.items():
        if type(v) is dict:
            replace_inf_nan_with_str(v)
        elif type(v) is float:
            if math.isinf(v) or math.isnan(v):
                d[k] = str(v)
    return d

if __name__ == "__main__":
    LiveApp.cli()
