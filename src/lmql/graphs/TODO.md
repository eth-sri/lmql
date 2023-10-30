* InferenceGraph.ainfer_branch: 
    - implement engine-based branching (e.g. cost based, confidence based, some callback to a engine strategy)
    - add support for enumerating all inference execution plans and then choosing and executing them selectively

* InferenceGraph.ainfer_branch/InferenceGraph.ainfer_call:
    - add support for cached inference results (e.g. cache by argument values and node type, e.g. annotate query function as @lmql.query(n=1))
        - decoder cache enabled by default (shared for same query node)

* InferenceGraph.ainfer:
    - add support for assertion failures => should be reflected in the instance node

* InferenceGraph
    - add support for asyncio.gather-based concurrent exploration of the graph

* merging.py
    - ByEmbedding: Merges text by embedding similarity
    - ByInt: Merges integer normalized by simple output parser
    - Think about separating the strategy for aggregating scores, e.g. addition, mean, max, min, etc.

* scoring
    - support weighted calls
    - support re-scored/weighted calls (e.g. 0.9 * a() or score(VALUE) * a(VALUE))

* check/add compiler support for branching calls with 3+ operands