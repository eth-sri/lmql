# Scripted Prompting

In LMQL, programs are not just static templates of text, as they also contain control flow (e.g. loops, conditions, function calls). This facilitates dynamic prompt construction and allows LMQL programs to respond dynamically to model output. This scripting mechanic is achieved by a combination of prompt templates, control flow and [output constraining](constraints.md).

> Note: LMQL requires special escaping to use `[`, `]`, `{` and `}` in a literal way, see [](Escaping).

**Packing List** For instance, let's say we want to generate a packing list before going on vacation. One way to do this would be the following query:

```{lmql}

name::list

"A few things not to forget when going to the sea (not travelling): \n"
"[LIST]"

model-output::
A list of things not to forget when going to the sea (not travelling):
[LIST -A phone with call, texting or tech services
-A copy of the local paper
-A pen or phone Keytar
]
```

Here, we specify a `sample` decoding algorithm for increased diversity over `argmax` (cf. [Decoders](decoders.md)), and then execute the program to generate a complete list using one `[LIST]` variable.


This can work well, however, it is unclear if the model will always produce a well-structured list of items. Further, we have to parse the response to separate the various items and process them further.

**Simple Prompt Templates** To address this, we can provide a more rigid template, by providing multiple prompt statements, one per item, to let the model only fill-in the `THING` variable:

```{lmql}

name::list-multi

"A list of things not to forget when going to the sea (not travelling): \n"
"-[THING]" where STOPS_AT(THING, "\n")
"-[THING]" where STOPS_AT(THING, "\n")
"-[THING]" where STOPS_AT(THING, "\n")
"-[THING]" where STOPS_AT(THING, "\n")
"-[THING]" where STOPS_AT(THING, "\n")

model-output::
A list of things not to forget when going to the sea (not travelling):
-[THING A phone with a/r text]
-[THING pletter]
-[THING accoon]
-[THING Films about/of the sea]
-[THING A has been in the Poconos for/ Entered the Poconos]
```

Note how we use a stopping constraint on each `THING`, such that a new line in the model output makes sure we progress with our provided template, instead of running-on with the model output. Without the stopping condition, simple template filling would not be possible, as the model would generate more than one item for the first variable already.

**Prompt with Control-Flow** Given this prompt template, we can now leverage control flow in our prompt, to further process results and avoid redundancy, while also guiding text generation. First, we simplify our query and use a `for` loop instead of repeating the variable ourselves:

```{lmql}

name::list-multi
"A list of things not to forget when going to the sea (not travelling): \n"
backpack = []
for i in range(5):
   "-[THING]" where STOPS_AT(THING, "\n") 
   backpack.append(THING.strip())
print(backpack)

model-output::
A list of things not to forget when going to the sea (not travelling):
-[THING A good pair of blue/gel saskaers]
-[THING A good sun tanner]
-[THING A good air freshener]
-[THING A good spot for washing your hands]
-[THING A good spot for washing your feet]

# print output: \['A good pair of blue/gel saskaers', 'A good sun tanner', 'A good air freshener', 'A good spot for washing your hands', 'A good spot for washing your feet'\]
```

Because we decode our list `THING` by `THING`, we can easily access the individual items, without having to think about parsing or validation. We just add them to a `backpack` list of things, which we then can process further.


**Inter-Variable Constraints** Now that we have a collected a list of things, we can even extend our program to constrain a follow-up LLM calls to choose among the things in our `backpack`:

```{lmql}

name::list-multi-follow

"A list of things not to forget when going to the sea (not travelling): \n"
backpack = []
for i in range(5):
   "-[THING]" where STOPS_AT(THING, "\n") 
   backpack.append(THING.strip())

"The most essential of which is: [ESSENTIAL_THING]" where ESSENTIAL_THING in backpack

model-output::
A list of things not to forget when going to the sea (not travelling): ⏎
-[THING Sunscreen]⏎
-[THING Beach Towels]⏎
-[THING Beach Umbrella]⏎
-[THING Beach Chairs]⏎
-[THING Beach Bag]⏎
The most essential of which is: [ESSENTIAL_THING Sunscreen]
```

This can be helpful in guiding the model to achieve complete and consistent model reasoning which is less likely to contradict itself.

(Escaping)=
## Escaping `[`, `]`, `{`, `}`


Inside prompt strings, the characters `[`, `]`, `{`, and `}` are reserved for template variable use and cannot be used directly. To use them as literals, they need to be escaped as `[[`, `]]`, `{{`, and `}}`, respectively. Beyond this, the [standard string escaping rules](https://www.w3schools.com/python/gloss_python_escape_characters.asp) for Python strings and [f-strings](https://peps.python.org/pep-0498/#escape-sequences) apply, as all top-level strings in LMQL are interpreted as Python f-strings.

For instance, if you want to use JSON syntax as part of your prompt string, you need to escape the curly braces and squared brackets as follows:

```{lmql}
name::bruno-mars-json

argmax 
    """
    Write a summary of Bruno Mars, the singer:
    {{
      "name": "[STRING_VALUE]",
      "age": [INT_VALUE],
      "top_songs": [[
         "[STRING_VALUE]",
         "[STRING_VALUE]"
      ]]
    }}
    """
from
    "openai/text-davinci-003" 
where
    STOPS_BEFORE(STRING_VALUE, '"') and INT(INT_VALUE) and len(TOKENS(INT_VALUE)) < 2
         
         
```

## Python Compatibility

Going beyond simple control flow, LMQL also supports most valid Python constructs in the prompt clause of a query, where top-level strings like `"-[THING]"` are automatically interpreted as model input and template variables are assigned accordingly. For more advanced usage, see also the [External Functions](functions.md) chapter.
