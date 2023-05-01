metadata:release: 2023-05-01 13:00:00 +0000
metadata:authors: team

# Releasing the LMQL Caching Layer (v0.0.6)

Today we are releasing LMQL 0.0.6, the first version of LMQL that integrates the *LMQL Caching Layer*. The caching layer can drastically reduce token use of LLM interaction, lowering both the cost and latency of running queries. In this blog post, we provide a quick overview of the caching layer and demonstrate how it can reduce token use, latency and the number of requests needed to run queries by up to 80%. We observe improvements across a wide range of different scenarios, including **template-based queries, long-form constraints and tool augmentation.**

You can experiment with LMQL in the browser-based [Playground IDE](http://lmql.ai/playground) or install the latest version locally, via `pip install lmql`.

## Caching Layer

The caching layer is implemented as a **tree-based data structure** that caches all model output including logits, tokens, and metadata, allowing the runtime to more efficiently explore the token space of an LLM, even in the presence of multiple variables, constraints and tool augmentation. The cache can be considered an append-only tree, that is explored during query execution, expanding branches according to query code, constraints and speculative execution.

To illustrate the effect of a caching layer, we consider the following example scenarios, all of which now run in a fraction of the time and with a fraction of the tokens needed with traditional querying methods.

### Template-Based Queries 

When specifying a prompt template with multiple variables to fill in, an LLM typically needs to be invoked once per variable. For instance, consider the following template that guides an LLM in generating a list of things:
```{lmql}
name::list-of-things-speculative
argmax
    "A list of things not to forget when going to the sea (not travelling): \n"
    "- Sunglasses \n"
    "-[THING]"
    "-[THING]"
    "-[THING]"
    "-[THING]"
from
    'openai/text-ada-001'
where
    STOPS_AT(THING, "\n")
```
**Without Caching:** Tokens: 390, Requests: 4 | **With Caching Layer:** Tokens: 89 (<span style="color: green">-77%</span>), Requests: 1 (<span style="color: green">-75%</span>)

Here, the LLM typically needs to be invoked 4 times, once per `[THING]` variable. On each call, this incurs a token and latency cost (both with OpenAI and local models). Separate calls are needed, because our template dictates the `-` token to be inserted before each `[THING]`. 

With the caching layer, LMQL can now invoke the LLM only once, and fill in all variables with the resulting tokens, as long as the LLM output already aligns naturally with your template. In case the LLM result of the initial invocation at some point no longer aligns with the template, LMQL will automatically re-invoke the LLM from this point on, guaranteeing an overall consistent result that is already parsed into separate `[THING]` variables.

### Short-Circuiting Long Constraints

When you specify long constraints like `A in ["ABCDE", "FGHIJK"]`, the LMQL runtime guides the LLM to choose one of the provided options and then continues enforcing the sequence until the chosen values is fully decoded. To illustrate, consider the following query:
```{lmql}
name::long-form-constraints-speculative
argmax
    "If we have the choice we choose[OPTION]"
from 
    "openai/text-ada-001"
where
    OPTION in ["Option A with a whole lot of extra context", 
        "Option B with context", 
        "Another Option, also with a lot of additional text"
    ]
model-output::
If we have the choice we choose [OPTION Option A with a whole lot of extra context]
```
**Without Caching:** Tokens: 123, Requests: 9 | **With Caching Layer:** Tokens: 25 (<span style="color: green">-80%</span>), Requests: 2 (<span style="color: green">-78%</span>)

Here, after the LLM has produced `"Option"` and then `" A"`, LMQL short-circuits further model calls and automatically completes the resulting sequence to `"Option A with a whole lot of extra context"`. This is possible because once `Option A` has been predicted, the remaining tokens are fully determined by the constraints.

### Tool-Augmented Queries

Lastly, we consider tool augmented queries. LLM agents and tool augmentation are very powerful paradigms, that allow LLMs to incorporate external knowledge and reasoning into their predictions. However, this comes at a cost: On each tool invocation, the LLM needs to be re-invoked to continue decoding after the tool output has been inserted. This impacts both the token cost and latency of running queries, as many requests have to be send forth and back between the LLM and the tool.

As an example, consider the following query that augments an LLM with the ability to use a key-value storage, [also runnable in the browser-based LMQL Playground](http://lmql.ai/playground?snippet=kv).

<center>
<a href="http://lmql.ai/playground?snippet=kv">
    <img src="https://user-images.githubusercontent.com/17903049/235436824-0150f73f-0ac6-4cd9-8cc9-d13343da54f0.png" alt="Key-Storage Augmented LLM implemented in LMQL" style="height:320pt;"/>
</a>
</center>

**Without Caching:** Tokens: 5,162, Requests: 12 | **With Caching Layer:** Tokens: 3,481 (<span style="color: green">-33%</span>), Requests: 8 (<span style="color: green">-33%</span>)

Here, whenever the LLM produces an action relating to our key-value storage, we invoke a tool that handles the storage and return the result (to `assign` and `get` stored values). The result of each tool invocation is then inserted into the LLM output, and the LLM is re-invoked to continue decoding.

We count 10 tool interactions which results in 12 requests if we run without caching. However, using the new caching layer, we can reduce this to 8 requests, even undercutting the number of tool interactions. This is possible because the caching layer will not abort LLM generation, if the LLM already correctly predicts the tool output. 

This scenario demonstrates that the natural ability of LLMs to complete sequences can be leveraged to reduce the number of tool interactions, by relying on speculative execution.

## Persisting the Cache

Of course, the in-memory cache of the LMQL runtime can also be persisted to disk, allowing you to reuse the cache tree across multiple queries, automatically reducing token cost and latency. In some cases this can even be used to reduce the number of requests to the LLM to 0, e.g. if the cache already contains the desired result. 

To do so, you can simply specify a `cache="file.tokens"` parameter in your query code:

```{lmql}
name::joke-with-cache
argmax(cache="joke.tokens")
   """A good dad joke. A indicates the punchline
   Q:[JOKE]
   A:[PUNCHLINE]"""
from
   "openai/text-davinci-003"
where
   len(JOKE) < 120 and 
   STOPS_AT(JOKE, "?") and 
   STOPS_AT(PUNCHLINE, "\n") and 
   len(PUNCHLINE) > 1
```

The first successful run of this query will persist the cache to `joke.tokens`. Subsequent runs will then automatically load the cache from disk, and only invoke the LLM if the cache does not contain a match. This also works for queries whose underlying LLM requests only partially overlap, as the tree-based cache data structure will automatically identify matching subtrees.

**Caching During Query Development**: Persisting the cache can be particularly useful during query development, as it allows you to reuse the cache across multiple runs of the same query. A persistent cache will reduce token cost and latency of your query, even if you slightly change the query between runs.

## Caveats and Disabling the Cache

You can disable the caching layer by specifying `cache=False` in your query code. This will cause the LMQL runtime to always invoke the LLM, and never use the cache. This is useful for debugging purposes, or if you want to ensure that the LLM is always invoked.

Further, as the cache currently is implemented as an append-only data structure, it will grow indefinitely. This may be problematic for long-running applications, as the cache will eventually grow to relatively large sizes. In the future, we plan to implement simple strategies to limit the cache size, such as a least-recently-used eviction policy.

## Conclusion

In this post, we introduced the new caching layer of the LMQL runtime, which allows you to reduce the token cost and latency of your queries by reusing previously generated LLM outputs. We demonstrated how the caching layer can be used to reduce the number of LLM invocations in a variety of scenarios, including long constraints, short-circuiting, and tool-augmented queries. We also showed how the cache can be persisted to disk, allowing you to reuse the cache across multiple queries.

To learn more about LMQL please also check out our [documentation](https://docs.lmql.ai), or join our [Discord](https://discord.gg/2Y3Wz2Q) to chat with us directly. We are looking forward to hearing from you!