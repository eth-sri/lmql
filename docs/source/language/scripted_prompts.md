# Scripted Prompting

In LMQL, prompts are not just static text, but can also contain control flow (e.g. loops, conditions, function calls). This facilitates dynamic prompt construction and allows LMQL queries to respond dynamically to model output. Overall, scripted prompting is achieved by a combination of prompt templates, control flow and [output constraining](constraints.md).

For instance, let's say we want to generate a packing list. One way to do this would be with the following query:

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

This can work well, however, it is unclear if the model will always produce a well-structured list of items. Further, we have to parse the response to separate it into separate items and process it further.

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

**Prompts with Control-Flow** Lastly, leveraging control flow, we can simplify our query and use a `for` loop instead of repeating the variable ourselves:

```{lmql}

name::list-multi
sample(temperature=0.8)
   "A list of things not to forget when going to the sea (not travelling): \n"
   for i in range(5):
      "-[THING]"
from
   'openai/text-ada-001'
where
   STOPS_AT(THING, "\n")
```

```model-output
A list of things not to forget when going to the sea (not travelling):
-Cage
-Sieve
-King
-Crow
-Seaweed
```



Now, we can easily adapt the number of generated items using the number of iterations of our `for` loop.