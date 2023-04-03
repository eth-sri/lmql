# Constraints

LMQL allows you to specify constraints on the language model output. This is valuable in scripted prompting to ensure the model output stops at the desired point, but also allows to guide the model during decoding.

## Stopping Phrases
For many prompts, scripted prompts in particular, it is important to ensure that the model stops decoding once a certain word or symbol is reached. To do so, LMQL supports the `STOPS_AT` constraint. It takes two arguments, the first is the name of the variable to which the model output is assigned, the second is the stopping phrase. 

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

**Note:** If multiple variables in the query have the same name, the constraint is applied to all of them.


## General Constraints
Several constraints can be combined with the `and` and `or` keywords, recovering a Python boolean expression over the variables utilized in the LMQL query.
