metadata:release: 2023-04-17 13:30:00 +0000
metadata:authors: team

# LMQL Release 0.0.5

Today we are releasing version 0.0.5 of LMQL. This release focuses on stability and performance improvements. For a detailed list of changes, please see below. We are particularly excited about the first community contributions that have been merged as part of this release, with many more in the works.

`lmql==0.0.5` has been published on [PyPI](https://pypi.org/project/lmql/), based the current `main` branch of the [GitHub repository](https://github.com/eth-sri/lmql). The updated version has also been deployed to the browser-based [lmql.ai/playground](http://lmql.ai/playground).

### Changelog

* **Decoder Performance** The `argmax` and `sample` decoders have undergone some optimizations, allowing them to run faster. This results in a *20-30% speed-up* on common query workloads. [#24](https://github.com/eth-sri/lmql/pull/24).

* **Postprocessing Semantics** Internally, LMQL now allows constraints to implement postprocessing semantics. This is used to convert variable values after they have been completed, to a more normalized form in the prompt, and to a semantically meaningful data type in the context of the query code. [#24](https://github.com/eth-sri/lmql/pull/24). 

   For example, when using an `INT(<var>)` constraint on a generated number, the model will be restricted to only generate valid integers, and now, the resulting `NUM` value will additionally be converted to an `int` value:

   <div class="highlight lmql"><button href="" onclick="openPlaygroundSnippet(this, 'doc-snippets/releases-release-0-0-5-md-postprocessing-int-value')">Open In Playground</button><pre><span></span><span class="kp">argmax</span>
   <span class="s2">"My favorite number is: [NUM]</span><span class="se">\n</span><span class="s2">"</span>
   <span class="nb">print</span><span class="p">(</span><span class="nb">type</span><span class="p">(</span><span class="n">NUM</span><span class="p">),</span> <span class="n">NUM</span> <span class="o">*</span> <span class="mi">2</span><span class="p">)</span> <span class="c1"># &lt;class 'int'&gt; 4</span>
   <span class="s2">"Number times two is {NUM * 2}"</span>
   <span class="kn">from</span>
      <span class="s1">'openai/text-ada-001'</span>
   <span class="kp">where</span>
      <span class="n">INT</span><span class="p">(</span><span class="n">NUM</span><span class="p">)</span> </pre></div>

* **Core Interpreter** A complete reimplementation of the LMQL core interpreter has been completed. This fixes a couple of minor issues and overall, improves reliability and performance when dealing with *branching* decoding algorithms. [#24](https://github.com/eth-sri/lmql/pull/24).


* **Playground** Locally and when used in-browser, the [LMQL Playground](http://lmql.ai/playground) now *streams debugger information* from the LMQL interpreter incrementally. This leads to speed-ups when running in the Playground, especially with longer outputs. [#27f9a8ad](https://github.com/eth-sri/lmql/commit/27f9a8adb819f732608ef61c9aca9dca579dc536).


* **Other Fixes**:
    - When used from within Python (as decorated function), LMQL code no longer has to be doubly-escaped, e.g. you can now write `STOPS_AT(VAR, "\n")` instead of `STOPS_AT(VAR, "\\n")`
    - The LMQL inference API buffers requests that come in during startup, to avoid errors when the server is not yet ready. [#15](https://github.com/eth-sri/lmql/pull/15), thanks to [@chrispan](https://github.com/chrispan).
    - OpenAI request parallelization no longer leads to an error on Linux systems, with regards to worker processes [#6](https://github.com/eth-sri/lmql/issues/6).

### Preview

Apart from the changes above, we are also working on a number of other features, including:

* **llama.cpp support** as started in [this PR](https://github.com/eth-sri/lmql/pull/18), thanks to [@CircArgs](https://github.com/CircArgs).
* Support for **Type Constraints**, e.g.  `type(VAR) is DataClass`, that automatically force the model to produce a value that structurally conforms to the given type. See this [Twitter thread](https://twitter.com/lbeurerkellner/status/1646187597901733889) for more details.
* Support for using **Antlr parsers** during query execution, to force the model to produce a value that conforms to a given grammar. 

* **Extending Logit Masking to OpenAI Chat Models**. This will enable full support for LMQL constraints with e.g. `chatgpt` and `gpt-4` models. See [#25](https://github.com/eth-sri/lmql/pull/25), thanks to [@kharvd](https://github.com/kharvd).