import os

class DebuggerOutputWriter:
    def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables): pass
    def add_compiler_output(self, code): pass

class PrintingDebuggerOutputWriter:
    def __init__(self):
        self.clear = False
        self.print_output = True

    def add_decoder_state(*args, **kwargs): 
        pass

    def add_interpreter_head_state(self, variable, head, prompt, where, trace, is_valid, is_final, mask, num_tokens, program_variables):
        if head == 0:
            if self.clear:
                os.system("clear")
            if self.print_output:
                print(f"{prompt}\n\n valid={is_valid}, final={is_final}")
    def add_compiler_output(self, code): pass