# Constraints

LMQL allows you to specify constraints on the language model output. This is valuable in scripted prompting to ensure the model output stops at the desired point, but also allows to guide the model during decoding.

**Token Masking and Eager Validation** LMQL constraints are evaluated eagerly on each generated token, and will be used by the runtime to generate token masks during generation. This means, that the provided constraints are either satisfied by directly guiding the model during generation appropriately or, if this is not possible, validation will fail early on during generation, saving the cost of generating invalid output. In case of greedy decoding, this terminates the generation process, in case of branching decoding, it will prune the branch and continue generation only in the remaining, valid branches.

**High-Level Text Constraints** Constraints are high-level and operate on a text (not token) level. For instance, users can specify constraints like `VAR in ["Hello", "Hi", "Greetings"]`, without having to consider the exact tokenization of the individual phrases. LMQL will automatically translate these constraints to token masks, that can be used to guide the model during generation, allowing to generate output that satisfies the provided constraint using one generation call only.

This chapter provides an overview of the set of currently available constraints. Beyond that, LMQL constraint support is modular and extendible. If you are interested in implementing your own constraint, please see [Custom Constraints](#custom-constraints).

## Stopping Phrases and Type Constraints
For many prompts, scripted prompts in particular, it is important to ensure that the model stops decoding once a certain word or symbol is reached. To do so, LMQL supports the `STOPS_AT` constraint. It takes two arguments, the first is the name of the variable to which the model output is assigned, the second is the stopping phrase. 
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

### Custom Constraints

LMQL implements partial evaluation semantics for the `where` clause of a query, to enable eager validation. Further, it also defines additional semantics that allow to derive token-level prediction masks, using a limited form of symbolic execution.

To inspect the implementation of the different built-in constraint operators, see the file `src/lmql/ops/ops.py`. In general, a LMQL constraint operator is defined on three levels:

* *Value Semantics*: This is the literal level of an operator. For instance, the value of operation `len(VAR)` for a template variable `VAR` is the character length of the current model output assigned to `VAR`.

* *Final Semantics*: This is the level of operator semantics that allow the LMQL runtime to derive whether a computed value is final with respect to the current model output, or not. More formally, a value is considered final, if for any possible continuation of model output, the value will no longer change. For instance, the final value of `len(VAR)` is `fin` (final), if `VAR` has finished generation (cannot change anymore), and `inc` if generation is still ongoing (value will only increase). In the more general case, the finalness can also be `dec` for decreasing values, and `var` for values that may still increase or decrease.

* *Follow Semantics*: Lastly, the follow semantics of an operator, are given by a case-wise function, where each case defines value and final semantics, for a subset of possible continuation tokens. For instance, the follow semantics of `len(VAR)`, given a template variable `VAR`, is defined as follows:

   ```python
   len(VAR) = len(old(VAR)) + n where len(token) == n # a token of length n is generated next
   len(VAR) = len(old(VAR)) where token == "<|endoftext|>" # the model ends generation of VAR with the <|endoftext|> token
   ```

Given a value, final and follow implementation of a custom operator, it can be used modularly together with all other available LMQL operators. This includes operators that may enforce regular expressions or context-free grammars on the model output. For more details on custom operators, see the [LMQL paper](https://arxiv.org/abs/2212.06094).

### Expressiveness of LMQL Constraints

LMQL constraints are applied eagerly during generation by relying on distribution masking. This means, that the model will not be able to generate any tokens that are masked by the constraints. However, naturally, this approach is limited with respects to expressiveness, since not all properties on text can be decided on a token-by-token basis. More specifically, expressiveness is limited to the validation of [context-free languages](https://en.wikipedia.org/wiki/Context-free_grammar). To enable safe use of token masking, LMQL's implementation of final/follow semantics provide a soundness guarantee with respect to token masking (see [LMQL paper](https://arxiv.org/abs/2212.06094)).

Nonetheless, due to eager evaluation of constraints during generation, LMQL constraints will trigger as soon as the model output violates the constraint definitively (i.e. the validation result is final), preventing the model from the costly generation of invalid output. This is an advantage over the more common approach of post-processing the model output, which is typically only able to validate the output after it has been generated fully.