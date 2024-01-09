---
outline: [2,3]
---

# Constraints

<div class="subtitle">Controlled, type-safe LLM generation with guarantees.</div>

LMQL allows you to specify constraints on the language model output. This is valuable in scripted prompting, to ensure the model output stops at the desired point, but also allows you to guide the model during decoding.

This chapter provides an overview of the set of currently available constraints and a brief description of their semantics. Beyond that, LMQL constraint support is modular and can also be extended, as discussed in more detail in [Custom Constraints](./constraints/custom-constraints.md).

## Supported Constraints

### Stopping Phrases
For many prompts, scripted prompts in particular, it is important to ensure that the model stops decoding once a certain word or symbol is reached. To do so, LMQL supports the `STOPS_AT` and `STOPS_BEFORE` constraint. They take two arguments, the first is the name of the variable to which the model output is assigned, the second is the stopping phrase. 

In the example below we use stopping conditions to ensure that as soon as the model predicts the newline character `\n` the decoding of the current `THING` variable ends, and the query program continues execution.

```{lmql}

name::list-multi
"A list of things not to forget when going to the sea (not travelling): \n"
for i in range(5):
   "-[THING]" where STOPS_AT(THING, "\n")
```
```promptdown
A list of things not to forget when going to the sea (not travelling): 
- [THING|Sunscreen]
- [THING|Beach towels]
- [THING|Swimsuit]
- [THING|Sunglasses]
- [THING|Hat]
```

::: tip 
If multiple variables in the query have the same name, the constraint is applied to all of them.
::::

### Number Type Constraints

The data type of a generated variable can also be constrained. For example, we can constrain a variable to be a string, encoding an integer by using `INT`:

```{lmql}
name::number
"A number: [N]" where INT(N)
```
```promptdown
A number: [N|2]
```

This enforces that the model cannot generate tokens that do not correspond to an integer. 

::: info 
LMQL currently only supports integer constraints. However, support for floating point numbers and other types is planned for future releases. 
:::

### Choice From Set
LMQL allows to specify that a variable should be a choice from a set of possible values. This can be rephrased as the variable being within a  set of possible values, i.e. `THING in set(["Volleyball", "Sunscreen", "Bathing Suit"])` in the following example

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
   THING in set(["Volleyball", "Sunscreen", "Bathing Suit"])

```
```promptdown
A list of things not to forget when going to the sea (not travelling):
- [THING|Sunglasses]
- [THING|Sunscreen]
- [THING|Volleyball]
- [THING|Sunscreen]
- [THING|Sunscreen]
```

### Character Length 
Similar to Python, the `len` function can be used to refer to the length of a variable and can thus be used to add constraints on it's length on a character level.

```{lmql}
name::length
argmax
   "Hello [NAME]"
from
   'openai/text-ada-001'
where
    len(NAME) < 10

```
```promptdown
Hello [NAME| ⏎
⏎
I am in]
```

### Token Length 

Next to character-level length constraints, you can also specify constraints on the token length of a variable. This is useful if you want to ensure that the model does not generate too many tokens for a given variable. For instance, in the following example, we constrain the length of the variable `THING` to be at most 3 tokens:

```{lmql}
name::token-length
"Greet the user in four different ways: [GREETINGS]" \
   where len(TOKENS(GREETINGS)) < 10
```
```promptdown
Greet the user in four different ways: [GREETINGS|⏎
⏎
1. Hello there! It's nice]
```

Similar to character length constraints, the `len` function can also be used to refer to the number of `TOKENS(GREETINGS)`. However, now, length is measured in tokens, not characters. The exact resulting character length of the output thus depends on the tokenization of the model, however. 

Token length constraints are cheaper to enforce than character length constraints, as they can be implemented as simple length checks on the tokenized output, rather than the more expensive character-level length checks, which require detokenization and masking.

### Regex Constraints <span class="badge">Preview</span>

LMQL also supports `REGEX` constraints. This allows you to enforce a regular expression during generation of a variable. 

As a simple example, consider the following snippet:

```lmql
"It's the last day of June so today is [DATE]" \
   where REGEX(DATE, r"[0-9]{2}/[0-9]{2}")
```
```promptdown
It's the last day of June so today is [DATE|30/06]
```

::: tip PREVIEW FEATURE
`REGEX` constraints are currently in preview, which means that they may not function as expected in all cases. If you encounter problems, please report them in LMQL's issue tracker on GitHub.
:::



### Combining Constraints
Several constraints can be combined with the `and` and `or` keywords, recovering a Python boolean expression over the variables utilized in the LMQL query.

For example, the following program uses, both, a token length constraint and a stopping condition, to generate a short story:

```lmql
"A story about life:[STORY]" \
   where STOPS_AT(STORY, ".") and len(TOKENS(STORY)) > 40
```
```promptdown
A story about life:

[STORY(color=yellow)|Life is a journey filled with ups and downs, twists and turns, and unexpected surprises. It is a story that is unique to each individual, with its own set of challenges and triumphs.

For some, life begins with a loving family and a comfortable home, while for others it may start with struggle and hardship.]
```

Here, we enforce a stopping condition on the `.` character, but only once the generated story is at least 40 tokens long. Thus, the interpretation of `and` with stopping conditions is that the stopping condition is only enforced once the other constraints are satisfied.

## How Do LMQL Constraints Work?

**Token Masking and Eager Validation** LMQL constraints are evaluated eagerly on each generated token, and will be used by the runtime to generate token masks during generation. This means, that the provided constraints are either satisfied by directly guiding the model during generation appropriately or, if this is not possible, validation will fail early on during generation, saving the cost of generating invalid output. In case of greedy decoding (`sample` or `argmax`), this terminates the generation process, in case of branching decoding, it will prune the current branch and continue generation only in the remaining, valid branches.

**High-Level Text Constraints** Constraints are high-level and operate on a text (not token) level. For instance, users can specify constraints like `VAR in ["Hello", "Hi", "Greetings"]`, without having to consider the exact tokenization of the individual phrases. LMQL will automatically translate these constraints to token masks, that can be used to guide the model during generation, allowing to generate output that satisfies the provided constraint using one generation call only.


### Custom Constraints and Theoretical Background

To learn more about the internals of LMQL and how to implement your own LMQL constraint, see the chapter on [Implementing Custom LMQL Constraints](./constraints/custom-constraints.md). 
