# Scripted Prompting

In LMQL, prompts are not just static text, as they can also contain control flow (e.g. loops, conditions, function calls). This facilitates dynamic prompt construction and allows LMQL queries to respond dynamically to model output. This scripting mechanic is achieved by a combination of prompt templates, control flow and [output constraining](constraints.md).

**Packing List** For instance, let's say we want to generate a packing list. One way to do this would be the following query:

```{lmql}
  
name::list
sample(temperature=0.8)
   "A few things not to forget when going to the sea (not travelling): \n"
   "[LIST]"
from
   'openai/text-ada-001'
```

```model-output
A list of things not to forget when going to the sea (not travelling):

-A phone with call, texting or tech services
-A copy of the local paper
-A pen or phone Keytar
```

This can work well, however, it is unclear if the model will always produce a well-structured list of items. Further, we have to parse the response to separate the various items and process them further.

**Simple Prompt Templates** To address this, we can provide a more rigid prompt template, where we already provide the output format and let the model only fill in the `THING` variable:

```{lmql}

name::list-multi
sample(temperature=0.8)
   "A list of things not to forget when going to the sea (not travelling): \n"
   "-[THING]"
   "-[THING]"
   "-[THING]"
   "-[THING]"
   "-[THING]"
from
   'openai/text-ada-001'
where
   STOPS_AT(THING, "\n")
```

```model-output
A list of things not to forget when going to the sea (not travelling):
-A phone with a/r text
-pletter
-accoon
-Films about/of the sea
-A has been in the Poconos for/ Entered the Poconos
```

Note how we use a stopping condition on `THING`, such that a new line in the model output leads to a continuation of our provided template. Without the stopping condition, simple template filling would not be possible, as the model would generate more than one items for the first variable already.

**Prompt with Control-Flow** Given this prompt template, we can now leverage control flow in our prompt, to further process results, while also guiding text generation. First, we simplify our query and use a `for` loop instead of repeating the variable ourselves:

```{lmql}

name::list-multi
sample(temperature=0.8)
   "A list of things not to forget when going to the sea (not travelling): \n"
   backpack = []
   for i in range(5):
      "-[THING]"
      backpack.append(THING.strip())
   print(backpack)
from
   'openai/text-ada-001'
where
   STOPS_AT(THING, "\n")
```

```model-output
A list of things not to forget when going to the sea (not travelling):
-A good pair of blue/gel saskaers
-A good sun tanner
-A good air freshener
-A good spot forwashing your hands
-A good spot for washing your feet

# print output: ['A good pair of blue/gel saskaers', 'A good sun tanner', 'A good air freshener', 'A good spot forwashing your hands', 'A good spot for washing your feet']
```

Because we decode our list `THING` by `THING`, we can easily access the individual items, without having to think about parsing or validation. We just add them to a `backpack` list of things, which we then can process further.

## Python Compatibility

Going beyond simple control flow, LMQL supports most valid Python constructs in the prompt clause of a query, where top-level strings like `"-[THING]"` are automatically interpreted as model input and template variables are assigned accordingly. For more advanced usage, also see the [External Functions](functions.md) chaptor.