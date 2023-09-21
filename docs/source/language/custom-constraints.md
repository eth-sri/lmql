# Custom Constraints

LMQL's constraint language comes with a set of standard operators that can be combined. However, it is also possible to implement custom operations that enable the validation of more complex properties, while maintaining composability with built-in operations.

This chapter will explain how to implement a custom LMQL operator, using a two custom operators.

## Implementing a Custom Operator

To implement a custom operator, you need to define a class that inherits from `lmql.ops.Node`. The class must be decorated with the `@LMQLOp` decorator, which takes the name of the operator as an argument. The operator name can then be used in LMQL queries to refer to the custom operation.

The basic interface of a custom operator is given by the following methods:

```python
from lmql.ops import LMQLOp, Node, InOpStrInSet

@LMQLOp("custom_operator")
class CustomOperator(Node):
   # provides the value semantics of the operator
   def forward(self, *args, **kwargs):
      ...

   # provides a lookahead on the result of the operator (for next-token masking)
   def follow(self, *args, **kwargs):
      ...
    
   # provides the definitiveness of a result (temporary or final)
   def final(self, *args, **kwargs):
      ...
```


- `forward(self, *args, **kwargs)` This method implements the **forward semantics** of you operator, i.e. it determines the result of your operator `custom_operator(*args)`, i.e. whether something you are validating holds or does not hold for the specified arguments. This method is called for every token in the model output, and thus allows you to implement early stopping during generation.

- `follow(self, x, **kwargs)`: This method implements the **follow semantics** of your operator, i.e. it provides a lookahead on the result of your operator, given the current value of the specified arguments. The return value of this function is a so-called follow map, that differentiates among the different classes of continuation tokens. This method is called at least once on each token in the model output, to determine the set of allowed next tokens.

- `final(self, x, **kwargs)`: Lastly``, `final` implements the **final semantics** of your operator, i.e. it determines whether the result of your operator is final with respect to the current model output. This allows you to differentiate between temporary and final validation results, which is important to prevent early termination in cases of only temporary violations. 

   Possible return values are `"var"` and `"fin"` for temporary and final (definitive) results, respectively. Going beyond boolean logic, LMQL also supports `"inc"` and `"dec"` to indicate monotonically growing and shrinking results, respectively. This is useful character counting, strings and lists. For instance, the input variable `x` will have either `"inc"` final-ness, to indicate that it is a monotonically growing string (currently being generated), or `"fin"` final-ness, to indicate that it has reached its final value (query execution has completed decoding its value).

Depending on your use case, it may suffice to only implement `forward` (to enable early stopping during generation). However, for full masking support, you also have to implement `follow` and `final`.

## Example: Implementing a `foo`-`bar` Constraint

To demonstrate, we implement an operator that forces the model to always generate `bar` after generating `foo`. To clarify, the following sequences should be valid and invalid, respectively:

```python
"Hello foo!" # invalid
"Hello foo bar!" # valid
"Hello foo bar foo bar!" # valid
"Hello foo bar foo!" # invalid
```

To enforce this constraint, we implement a custom operator `foo_bar` as follows:

```python
import re
from lmql.ops import LMQLOp, Node, fmap, tset

@LMQLOp("foo_bar")
class FooBar(Node):
    def forward(self, x, **kwargs):
        # no restrictions, if x is not yet generated and there is no "foo" in x
        if x is None or "foo" not in x:
            return True

        # make sure foo is always followed by " bar"
        bar_segment = x.rsplit("foo",1)[1]
        return bar_segment.startswith(" bar") or len(bar_segment) == 0

    def follow(self, x, **kwargs):
        # (1) no restrictions, if x is not yet generated
        if x is None:
            return True
    
        # (2) no restrictions, if there is no "foo" in x
        if "foo" not in x:
            return True

        # (3) get current segment after last "foo"
        bar_segment = x.rsplit("foo",1)[1]
        
        # 3(a) already satisfied
        if bar_segment.startswith(" bar"):
            return True

        # 3(b) force continuations to align with " bar"
        return fmap(
            (tset(" bar", regex=True), True), # " bar" -> True
            ("*",          False) # anything else -> False
        )

    def final(self, x, result=None, **kwargs):
        # violations are definitive
        if not result: return "fin"
        # otherwise, depends on definitiveness of x
        return "fin" if x == "fin" else "var"
```

**forward() implementation**: First, we implement the `forward` method: To validate the `foo`-`bar` property, we check that any string segment following a potential `foo` substring aligns with `" bar"`. For this, we have to consider the case of x being none (not yet generated), a partial match (including empty strings), and a match that extends beyond `" bar"`. Depending on model tokenization `forward()` may be called on any such variation, and thus has to be able to handle all of them.

**follow() implementation**: Next, we implement the `follow` method. For this, we again consider multiple cases:

1. If `x` is not yet generated, we do not have to restrict the next token.
2. If there is no `foo` in `x`, we do not have to restrict the next token.
3. If there *is* a `foo` right at the end of `x`, we restrict as follows:

   **(a)** If the segment already starts with `" bar"`, no restrictions are necessary.

   **(b)** Otherwise, we restrict the next token to `" bar"`. For this, we construct a so-called *follow map*, a mapping of token ranges to the future evaluation result of our operator, if the next token is in the specified range. 
   
   In our `foo`-`bar` case it suffices to indicate that a continuation of ` bar` evaluates to `True`, and any other continuation to `False`. This is achieved by the `fmap` function, which constructs a follow map from a list of token ranges and their respective future evaluation results. To construct token ranges the [`tset` constructor](https://github.com/eth-sri/lmql/blob/main/src/lmql/ops/token_set.py#L535) can be used, which allows to select tokens by length, set, prefix or regex, independent from the concrete tokenizer in use. In this case we use the `regex=True` option, to automatically select all tokens that fully or partially match `" bar"`.

**final() implementation**: Lastly, we implement the `final` method. This indicates to the LMQL runtime, whether a result of our custom operator is final with respect to the current model output or temporary. In this case, a return value of `False` can always be considered final (a definitive violation, warranting early termination). Otherwise, we have to consider the definitiveness of the current value of `x`. If `x` is final, then the result of our operator is also final. Otherwise, it is temporary, as a further continuation of `x` may still result in satisfying the constraint.

> **Note:** For illustrative purposes, 3b of our `follow()` implementation simplifies an important detail about token alignment. It only consider the case, where `follow()` is called right at the end of `"foo"`, i.e. depending on model behavior and tokenization, `follow()` may also run on a partial result like `"foo b"`, where the correct follow map should indicate `"ar"` as valid continuation not the full `" bar"`. To handle this, one can simply rely on the implementation of built-in InOpStrInSet (implementation of constraint `VAR in [...]`), and replace the `fmap` call with `InOpStrInSet([]).follow(bar_segment, [" bar"])`, which will automatically handle all such cases.

### Using the Custom Constraint Operator

To use the custom constraint operator, you can simply import it in your query context and use it as follows:

```{lmql}
name::foo_bar_constraint

"Say 'foo':[A]" where foo_bar(A)
```

In general, you have to ensure that the `@LMQLOp` decorator is executed in your current process before the query is parsed, e.g. by importing the module containing the operator implementation. 


## What Happens Under the Hood?

Given an operator implementation as above, the LMQL runtime will be able to both validate model output during generation and derive token-level prediction masks. For this, `forward`, `follow` and `final` are called repeatedly during generation, with the current model output `x` as input. This allows the runtime to derive both validity of the current model output, as well as next-token ranges for which the operator definitively (`final`) evaluates to `False`. Based on the correctness of the underlying implementation, this soundly ensures that the model will never select a `follow`-masked token that would definitively violate your constraint.
<!-- 
### Theroretical Background

LMQL implements partial evaluation semantics for the `where` clause of a query, to enable eager validation. Further, it also defines additional semantics that allow to derive token-level prediction masks, using a limited form of symbolic execution.

To inspect the implementation of the different built-in constraint operators, see the file `src/lmql/ops/ops.py`. In general, a LMQL constraint operator is defined on three levels:

* *Value Semantics*: This is the literal level of an operator. For instance, the value of operation `len(VAR)` for a template variable `VAR` is the character length of the current model output assigned to `VAR`.

* *Final Semantics*: This is the level of operator semantics that allow the LMQL runtime to derive whether a computed value is final with respect to the current model output, or not. More formally, a value is considered final, if for any possible continuation of model output, the value will no longer change. For instance, the final value of `len(VAR)` is `fin` (final), if `VAR` has finished generation (cannot change anymore), and `inc` if generation is still ongoing (value will only increase). In the more general case, the finalness can also be `dec` for decreasing values, and `var` for values that may still increase or decrease.

* *Follow Semantics*: Lastly, the follow semantics of an operator, are given by a case-wise function, where each case defines value and final semantics, for a subset of possible continuation tokens. For instance, the follow semantics of `len(VAR)`, given a template variable `VAR`, is defined as follows:

   ```python
   len(VAR) = len(old(VAR)) + n where len(token) == n # a token of length n is generated next
   len(VAR) = len(old(VAR)) where token == "<|endoftext|>" # the model ends generation of VAR with the <|endoftext|> token
   ```

Given a value, final and follow implementation of a custom operator, it can be used modularly together with all other available LMQL operators. This includes operators that may enforce regular expressions or context-free grammars on the model output. For more details on custom operators, see the [LMQL paper](https://arxiv.org/abs/2212.06094). -->

## Expressiveness of LMQL Constraints

LMQL constraints are applied eagerly during generation by relying on token masking. This means, that the model will not be able to generate any tokens that are masked by the constraints. However, naturally, this approach is limited with respects to expressiveness, since not all properties on text can be decided on a token-by-token basis. More specifically, expressiveness is limited to the validation of [context-free languages](https://en.wikipedia.org/wiki/Context-free_grammar). To enable safe use of token masking, LMQL's implementation of final/follow semantics provide a soundness guarantee with respect to token masking (see [LMQL paper](https://arxiv.org/abs/2212.06094)).

Nonetheless, due to eager evaluation of constraints during generation, LMQL constraints will trigger as soon as the model output violates the constraint definitively (i.e. the validation result is final), preventing the model from the costly generation of invalid output. This is an advantage over validation in post-processing, where violations may only be detected after the model has already generated a large amount of invalid output.