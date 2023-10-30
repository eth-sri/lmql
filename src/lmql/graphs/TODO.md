* check/add compiler support for branching calls with 3+ operands
* InferenceGraph.ainfer_branch: 
    - implement engine-based branching (e.g. cost based, confidence based, some callback to a engine strategy)

* InferenceGraph.ainfer:
    - apply state merging by @lmql.query annotated method, after InstanceNode has been created (state merging should reflect in instance node hierarchy)