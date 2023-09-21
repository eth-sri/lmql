# Constraints

LMQL allows you to specify constraints on the language model output. This is valuable in scripted prompting to ensure the model output stops at the desired point, but also allows you to guide the model during decoding.

**Token Masking and Eager Validation** LMQL constraints are evaluated eagerly on each generated token, and will be used by the runtime to generate token masks during generation. This means, that the provided constraints are either satisfied by directly guiding the model during generation appropriately or, if this is not possible, validation will fail early on during generation, saving the cost of generating invalid output. In case of greedy decoding (`sample` or `argmax`), this terminates the generation process, in case of branching decoding, it will prune the branch and continue generation only in the remaining, valid branches.

**High-Level Text Constraints** Constraints are high-level and operate on a text (not token) level. For instance, users can specify constraints like `VAR in ["Hello", "Hi", "Greetings"]`, without having to consider the exact tokenization of the individual phrases. LMQL will automatically translate these constraints to token masks, that can be used to guide the model during generation, allowing to generate output that satisfies the provided constraint using one generation call only.

This chapter provides an overview of the set of currently available constraints and a brief description of their semantics. Beyond that, LMQL constraint support is modular and extendible. If you are interested in implementing your own constraint, please see [Custom Constraints](./custom-constraints.md).

## Stopping Phrases and Type Constraints
For many prompts, scripted prompts in particular, it is important to ensure that the model stops decoding once a certain word or symbol is reached. To do so, LMQL supports the `STOPS_AT` and `STOPS_BEFORE` constraint. They take two arguments, the first is the name of the variable to which the model output is assigned, the second is the stopping phrase. 
In the example below we use it to ensure that as soon as the model predicts the newline character `\n` the decoding of the variable `THING` is stopped, and prompt clause continues execution.

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

In a similar manner we can constrain a variable to be a string encoding an integer by using `INT`:

```{lmql}
name::number
argmax
   "A number: [N]"
from
   'openai/text-ada-001'
where
    INT(N)

model-output::
A number: [N 2]
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

model-output::
A list of things not to forget when going to the sea (not travelling): ⏎
- [THING Sunglasses] ⏎
- [THING Sunscreen] ⏎
- [THING Volleyball] ⏎
- [THING Sunscreen] ⏎
- [THING Sunscreen] ⏎
```

## Length 
Similar to Python, the `len` function can be used to refer to the length of a variable and can thus be used to add constraints on it's length.

```{lmql}
name::length
argmax
   "Hello [NAME]"
from
   'openai/text-3a-001'
where
    len(NAME) < 10

model-output::
Hello [NAME ⏎
⏎
I am in]
```

## Combining Constraints
Several constraints can be combined with the `and` and `or` keywords, recovering a Python boolean expression over the variables utilized in the LMQL query.

## Custom Constraints and Theoretical Background

To learn more about the internals of LMQL and how to implement your own LMQL constraint, see the chapter on [Implementing Custom LMQL Constraints](./custom-constraints.md). 

```{toctree}

./custom-constraints
```