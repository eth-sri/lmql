"""
LMQL decorators are user-provided functions that can be used to hook into the query execution
process and on a per-variable basis.
"""

import inspect
from lmql.language.qstrings import TemplateVariable
from lmql.runtime.program_state import ProgramState

class LMQLDecorator:
    """
    Base class for an LMQL decorator. An LMQL decorator is a function that is invoked during
    generation of an annotated placeholder variable, e.g. `"[@my_decorator_fn RESULT]"`.

    See the method docstrings for more information on the different stages a decorator is
    invoked in, during query execution.
    """

    def pre(self, variable: TemplateVariable, context: ProgramState):
        """
        This method is invoked before a variable value is generated. 
        
        If the decorator does not just return the provided TemplateVariable, its return value will 
        instead be used as variable value, query execution will skip this variable, and continue
        with the next variable in the query.
        """
        return variable
    
    def stream(self, variable_value, context: ProgramState):
        """
        This method is continously invoked during query execution, whenever a new token is explored
        by the configured decoding algorithm. 
        
        Note that this method will be invoked many times and many different values for `variable_value`
        including duplicates and conflicting branches that are not actually part of the final output.

        For consistent output streaming, make sure to filter undesired intermediate values or configure 
        the decoding algorithm to only explore one branch.
        """
        return variable_value
    
    def post(self, variable_value, prompt_value, context: ProgramState):
        """
        This method is invoked after a variable value has finished generating and all constraint-imposed
        postprocessing has been applied.

        `variable_value` corresponds to the program value of the variable (e.g. a string or other data type),
        and `prompt_value` corresponds to string representation of `variable_value` as it will be used in the
        prompt going forward.

        A decorator can either return a new value for `variable_value` and `prompt_value` or return `None` to
        indicate that the values should not be changed. If a two-tuple is returned, the first value will be used
        as the new `variable_value` and the second value will be used as the new `prompt_value`. If only a single
        value is returned, it will be used as the new `variable_value` and `str(value)` will be used as the new
        `prompt_value`.
        """
        return variable_value, prompt_value

class LMQLDecoratorFunction(LMQLDecorator):
    """
    Wraps a provided callable as an LMQL (post-only) decorator. 
    """
    def __init__(self, decorator):
        self.post_fn = decorator
        self.num_args = len(inspect.signature(decorator).parameters)
    
    def post(self, variable_value, prompt_value, context: ProgramState):
        if self.num_args == 1:
            r = self.post_fn(variable_value)
        else: # self.num_args >= 2
            r = self.post_fn(variable_value, prompt_value, context)
        
        # If the decorator returns None, we don't want to change the value
        if r is None:
            return variable_value, prompt_value

        # If the decorator returns a tuple, we want to change both the variable and the prompt
        if isinstance(r, tuple):
            return r
        else:
            # otherwise, default to changing the variable and using str(r) in the prompt
            return r, str(r)

def wrap(decorator):
    """
    Converts a decorator-compatible expression into an LMQLDecorator instance.
    """
    if isinstance(decorator, LMQLDecorator):
        return decorator
    elif callable(decorator):
        return LMQLDecoratorFunction(decorator)
    else:
        raise TypeError(f"Not a valid decorator expression: {decorator}")

class LMQLDecoratorList(LMQLDecorator):
    """
    Invokes a list of decorators in order during the different stages of query execution,
    respecting forward and reverse order of execution for the different stages of query execution.

    pre: forward (like in 'decorators')
    stream: reverse (like in 'reversed(decorators)'))
    post: reverse (like in 'reversed(decorators)'))
    """
    def __init__(self, decorators):
        self.decorators = [wrap(decorator) for decorator in decorators]
    
    def pre(self, variable: TemplateVariable, context: ProgramState):
        initial_variable = variable
        
        for decorator in self.decorators:
            variable = decorator.pre(variable, context)

            # if a decorator prevents the variable from being generated, skip the remaining decorators
            if variable is not initial_variable:
                break
        
        # make sure to always return a variable, prompt tuple
        if variable is not initial_variable:
            if type(variable) is tuple:
                variable, prompt_value = variable
            else:
                prompt_value = str(variable)
            return variable, prompt_value

        return variable
    
    def stream(self, variable_value, context: ProgramState):
        for decorator in reversed(self.decorators):
            variable_value = decorator.stream(variable_value, context)
        return variable_value
    
    def post(self, variable_value, prompt_value, context: ProgramState):
        for decorator in reversed(self.decorators):
            variable_value, prompt_value = decorator.post(variable_value, prompt_value, context)
        return variable_value, prompt_value
    
class pre(LMQLDecorator):
    """
    Annotates a function as a pre-stage LMQL decorator. That is, the function will be called
    before the variable value is generated. The function should accept a single argument
    of type `TemplateVariable` and return a `TemplateVariable` instance or alternatively
    a pre-defined value for the variable.
    """
    def __init__(self, decorator_fn):
        self.decorator_fn = decorator_fn
        self.num_args = len(inspect.signature(decorator_fn).parameters)
    
    def pre(self, variable: ProgramState, context: ProgramState):
        if self.num_args == 1:
            return self.decorator_fn(variable)
        else: # self.num_args >= 2
            return self.decorator_fn(variable, context)

class streaming(LMQLDecorator):
    """
    Annotates a function as a streaming-stage LMQL decorator. That is, the function will be called
    on every new decoded token in the prompt.

    You can annotate and use a program function as a streaming decorator like so:
    
    ```
    @streaming_decorator
    def my_decorator_fn(variable_value, context):
        # ...

    argmax "Hello [@my_decorator_fn] World" from "<model>"
    ```

    This can be helpful e.g. to implement variable-specific output streaming.
    """

    def __init__(self, decorator_fn):
        self.decorator_fn = decorator_fn
    
    def stream(self, *args, **kwargs):
        r = self.decorator_fn(*args, **kwargs)
        if r is None: return args[0]
        else: return r
