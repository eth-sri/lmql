import lmql
from lmql.tests.expr_test_utils import run_all_tests

nl = "\n"

class Output:
   def __init__(self):
      self.output_vars = {}

   def add(self, vvar, value):
      if vvar in self.output_vars:
         self.output_vars[vvar].append(value)
      else:
         self.output_vars[vvar] = [value]

   def add_all(self, vvar, values):
      if vvar in self.output_vars:
         self.output_vars[vvar].extend(values)
      else:
         self.output_vars[vvar] = list(values)


@lmql.query
async def make_summary_option(o, option_text, length_limit, option_type):
   '''lmql
   offset = len(context.prompt)

   "{:user}Make a {option_text}"
   "{:assistant}[option]" where STOPS_AT(option, nl) and STOPS_AT(option, ".")
   if len(option) > length_limit:
      "{:user}The {option_text} is too long, make it shorter"
      "{:assistant}[option]" where STOPS_AT(option, nl) and STOPS_AT(option, ".")
   o.add(option_type, option.strip())
   '''

@lmql.query(model=lmql.model("local:llama.cpp:/lmql/llama-2-7b-chat.Q2_K.gguf", tokenizer="AyyYOO/Luna-AI-Llama2-Uncensored-FP16-sharded"))
async def test_summary_back2back():
    '''lmql
    o = Output()
    material_text = "This is a story about love."

    n_summaries = 2
    n_distractors = 2

    """{:system}The user wants to make an activity for the instructions `Select the sentences that are true in the text`.
    To do it they will ask you for `correct answers` or `distractors` for a particular text.
    Here is the text:

    {material_text}

    If you are asked for a correct answer more than once make them different.
    Only answer with the answer or distractor, nothing more.
    Your responses should be shorter than 100 characters.
    Avoid repetitive language.
    """
    length_limit = 120
    for i in range(n_summaries):
        '[correct_summaries: make_summary_option(o, "correct answer", length_limit, "correct_summaries")]'

    for i in range(n_distractors):
        '[incorrect_summaries: make_summary_option(o, "distractor", length_limit, "incorrect_summaries")]'
    '''
   
if __name__ == "__main__":
    run_all_tests(globals())