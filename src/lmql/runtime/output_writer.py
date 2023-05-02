import os
import termcolor

class BaseOutputWriter:
    def __init__(self, allows_input=True):
        self.allows_input = allows_input

    async def input(self, *args):
        if not self.allows_input:
            assert False, "current LMQL output writer does not allow input"
        return input(*args)

    async def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables): 
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