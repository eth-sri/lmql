metadata:release: 2023-07-13 18:00:00 +0000
metadata:authors: team

# LMQL becomes simpler and adds llama.cpp

Today we are releasing LMQL 0.0.6.5. This update contains a major simplification of the LMQL syntax, moving it much closer to standard Python. It also includes a `llama.cpp` based inference backend, several bug fixes and other minor improvements.

You can try the latest version of LMQL in your browser at [lmql.ai/playground](https://lmql.ai/playground) or install it via `pip install lmql`.

## One Line Is All It Takes

Most notably, 0.0.6.5 comes with several simplifications of the core syntax of LMQL. Of course, all changes are backwards compatible, so you can continue to use your existing query code and move to the new version without any changes.

With this, we aim to minimize syntactic overhead, employing sensible defaults to enable more concise programs like the following:

```{lmql}
name::simple-syntax

"One line is all it takes [CONTINUATION]"

model-output::
One line is all it takes [CONTINUATION Fallin' in love with me.]
```

**Sensible Defaults** This is possible because LMQL now automatically assumes `argmax` and `openai/text-davinci-003` as (configurable) default model. If you prefer to use 
a different model or custom decoder settings, you can still specify them explicitly, e.g. in the `@lmql.query` decorator function as demonstrated later in this post.

Without any additional configuration, the simple query code above translates to a full LMQL program like this:

```{lmql}
name::simple-syntax-default

argmax "One line is all it takes [CONTINUATION]" from "openai/text-davinci-003"
```

<br/>

### Inline Constraints

LMQL now allows you to specify several inline `where` constraints. This enables constraints that refer to local program variables, which means constraints can now be dependent on previous model outputs.

```{lmql}
name::list-with-array

"A list of awesome Dua Lipa songs:\n"
songs = []

"- New Rules\n"
for i in range(4):
    "-[SONG]\n" where STOPS_BEFORE(SONG, "\n")
    songs.append(SONG)

"Out of these, my favorite is[FAVORITE]" where FAVORITE in songs

model-output::
A list of awesome Dua Lipa songs:⏎
- New Rules
- [SONG Don't Start Now]
- [SONG IDGAF]
- [SONG Be the One]
- [SONG Blow Your Mind (Mwah)]
Out of these, my favorite is [FAVORITE Don't Start Now]
```

Note also how in this example LMQL code now reads much more like standard Python code, without any additional level of indentation. 

<br/>

### `@lmql.query` functions

The overhauled syntax also makes LMQL much  easier on the eyes when used with the `@lmql.query` [function decorator in Python](https://docs.lmql.ai/en/stable/python/python.html):

```python
import lmql
import json

@lmql.query(model="openai/text-curie-001", temperature=0.9)
def summarize(): '''lmql
    """
    Provide a summary of Dua Lipa, the pop icon:
    {{
      "name": "[STRING_VALUE]",
      "chart_position": [INT_VALUE],
      "top_songs": [[
         "[STRING_VALUE]",
         "[STRING_VALUE]"
      ]]
    }}
    """ where STOPS_BEFORE(STRING_VALUE, '"') and INT(INT_VALUE) and len(TOKENS(INT_VALUE)) < 3
    
    return json.loads(context.prompt.split("pop icon:",1)[1])'''

print(summarize()) # {'name': 'Dua Lipa', 'chart_position': 3415, 'top_songs': ['New Rules', 'Havana']}

```

<br/>

### `lmql.F` Lambda Functions

Based on LMQL's new minimal syntax, we introduce a novel and concise way to write LLM-based lambda functions. This offers a lightweight entryway to get started with integrated small LLM-based utilities in your code, without having to write a full LMQL program.

```python
import lmql

summarize = lmql.F("Summarize the following in a few words: {data}: [SUMMARY]")
main_subject = lmql.F("What is the main subject (noun) of the following text? {data}: [SUBJECT]", 
                      "len(TOKENS(SUBJECT)) < 20")

text = "In LMQL, users can specify high-level, logical constraints ..."

summarize(data=text) # LMQL enables high-level constraints to be enforced during text 
                     # generation, simplifying multi-part prompting and integration.
main_subject(data=text) # Language Model Query Language (LMQL)

```

<br/>
<br/>

## `llama.cpp` Inference Backend

LMQL now also fully integrates with the excellent [llama.cpp](https://github.com/ggerganov/llama.cpp) C++ implementation of a number of Transformer-based language models. 

Using `llama.cpp` from LMQL is as simple as specifying it in the `from` clause of a query:

```{lmql}
name::llama-cpp-blog

argmax "Say 'this is a test':[RESPONSE]" from "llama.cpp:<PATH TO WEIGHTS>.bin"
```

We support, both, in-process loading of `llama.cpp`, as well as remote inference via `lmql serve-model`. To learn more about `llama.cpp` and how to use it with LMQL, check out the corresponding chapter in the LMQL [documentation](https://docs.lmql.ai/en/latest/language/llama.cpp.html).

<br/>

## Other Changes

* LMQL now includes a `random` model backend, which randomly samples tokens from the GPT-2 vocabulary. This is useful for debugging and testing purposes and can be used for data generation in the context of highly constrained query programs.

* Two caching issues have been fixed, avoiding cache collisions which could lead to repeated model outputs.

* More robust query string parsing, allowing for [robust escaping](https://docs.lmql.ai/en/stable/language/scripted_prompts.html#escaping) of special characters `[`, `]`, `{` and `}`.

* Added support for `transformers` based Llama models and the associated (fast) implementation of HF tokenizers.

* Simplified Azure OpenAI support, see the relevant chapter in the [documentation](https://docs.lmql.ai/en/stable/language/azure.html).

We thank community members [@minosvasilias](https://github.com/minosvasilias) and [@CircArgs](https://github.com/CircArgs) for their contribution to this release.