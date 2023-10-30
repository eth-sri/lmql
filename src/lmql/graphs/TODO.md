* check/add compiler support for branching calls with 3+ operands

* InferenceGraph.ainfer_branch: 
    - implement engine-based branching (e.g. cost based, confidence based, some callback to a engine strategy)
    - add support for enumerating all inference execution plans and then choosing and executing them selectively

* InferenceGraph.ainfer_branch/InferenceGraph.ainfer_call:
    - add support for cached inference results (e.g. cache by argument values and node type, e.g. annotate query function as @lmql.query(n=1))

* InferenceGraph.ainfer:
    - apply state merging by @lmql.query annotated method, after InstanceNode has been created (state merging should reflect in instance node hierarchy)
    - add support for assertion failures => should be reflected in the instance node

* InferenceGraph
    - add support for asyncio.gather-based concurrent exploration of the graph