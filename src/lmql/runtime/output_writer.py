import os
import termcolor

class BaseOutputWriter:
    def __init__(self, allows_input=True):
        self.allows_input = allows_input

    async def input(self, *args):
        """
        Handle user input with an input prompt of *args. This is invoked when a query asks for user input via `await input()`.

        Returns:
            str: The user input.
        """
        if not self.allows_input:
            assert False, "current LMQL output writer does not allow input"
        return input(*args)

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables): 
        """
        Called whenever the query interpreter progresses in a meaningful way (e.g. new token added, new variable added, variable updated, etc.).

        Parameters:
            variable (str): 
                The name of the currently active variable.
            head (int): 
                The index of the current interpretation head (deprecated, will always be 0).
            prompt (str): 
                The full interaction trace/prompt of the query.
            where (object): 
                The AST representation of the queries validation condition.
            trace (object): 
                The evaluation trace of evaluating 'where' on the current program variables during generation.
            is_valid (bool): 
                Whether the current program variables satisfy the validation condition.
            is_final (bool): 
                Whether the value of 'valid' can be considered final (i.e. decoding more tokens will not change the value of 'valid').
            mask (np.ndarray): 
                Currently active token mask.
            num_tokens (int): 
                Number of tokens in the current 'prompt'.
            program_variables (ProgramState): 
                The current program state (lmql.runtime.program_state). E.g. program_variables.variable_values is a mapping of variable names to their current values.
        """
        pass

    def add_compiler_output(self, code): 
        pass

class PrintingOutputWriter:
    def __init__(self, clear=False):
        self.clear = clear
        self.print_output = True

    def add_decoder_state(*args, **kwargs): 
        pass

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        if head == 0:
            if self.clear:
                os.system("clear")
            if self.print_output:
                print(f"{prompt}\n\n valid={is_valid}, final={is_final}")
    
    def add_compiler_output(self, code): pass
    
class StreamingOutputWriter:
    def __init__(self, variable=None):
        self.variable = variable
        self.last_value = None
    
    def add_decoder_state(*args, **kwargs): 
        pass

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        if head == 0:
            if self.variable is not None:
                vars = self.variable
                if type(vars) is not list:
                    vars = [vars]
                
                value = "\n".join(program_variables.variable_values.get(v, "").strip() for v in vars)
                    
                # os.system("clear")
                if self.last_value is None:
                    self.last_value = value
                    print(value, end="", flush=True)
                else:
                    print(value[len(self.last_value):], end="", flush=True)
                    self.last_value = value
                return
            
            os.system("clear")
            print(f"{prompt}\n", end="\r")
            
    def add_compiler_output(self, code): pass

# ready to use output writer configurations
silent = BaseOutputWriter()
headless = BaseOutputWriter(allows_input=False)
stream = StreamingOutputWriter
printing = PrintingOutputWriter(clear=True)