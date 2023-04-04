# Constraints

LMQL allows you to specify constraints on the language model output. This is valuable in scripted prompting to ensure the model output stops at the desired point, but also allows to guide the model during decoding.

## Stopping Phrases
For many prompts, scripted prompts in particular, it is important to ensure that the model stops decoding once a certain word or symbol is reached. To do so, LMQL supports the `STOPS_AT` constraint. It takes two arguments, the first is the name of the variable to which the model output is assigned, the second is the stopping phrase. 
In the example below we use it to ensure that as soon as the model predicts the newline chacater `\n` the decoding of the variable `THING` is stopped.

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

## Choice From Set
LMQL allows to specify that a variable should be a choice from a set of possible values. This can be rephrased as the variable being within a  set of possible values, i.e. `THING in set(["Volleyball", "Sunscreen", "Bathing Suite"])` in the following example

```{lmql}
name::set
sample(temperature=0.8)
   "A list of things not to forget when going to the sea (not travelling): \n"
   "- Sunglasses \n"
   for i in range(4):
      "- [THING] \n"
from
   'openai/text-ada-001'
where
   THING in set(["Volleyball", "Sunscreen", "Bathing Suite"])
```

```model-output
A list of things not to forget when going to the sea (not travelling): ⏎
- Sunglasses ⏎
- Sunscreen ⏎
- Volleyball ⏎
- Sunscreen ⏎
- Sunscreen ⏎
```

## Length 
Similar to Python the `len` function can be used to refer to the length of a variable and can thus be used to add constraints on it's length.

```{lmql}
name::length
argmax
   "Hello [NAME]"
from
   'openai/text-ada-001'
where
    len(NAME) <> 3
```

```model-output
Hello ⏎
⏎
I am in
```

## Combining Constraints
Several constraints can be combined with the `and` and `or` keywords, recovering a Python boolean expression over the variables utilized in the LMQL query.
