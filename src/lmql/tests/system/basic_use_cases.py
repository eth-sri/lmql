import sys
sys.path.append("../")
import lmql
import asyncio
import time

from lmql.runtime.output_writer import PrintingDebuggerOutputWriter

class TestOutputWriter(PrintingDebuggerOutputWriter):
    def __init__(self):
        super().__init__()
        self.clear = False
        self.print_output = False

async def test_argmax_a_joke():
    query = """
argmax
 "A list of good dad jokes. A indicates the punchline \\n"
 "Q: How does a penguin build its house? \\n"
 "A: Igloos it together. END \\n"
 "Q: Which knight invented King Arthur's Round Table? \\n"
 "A: Sir Cumference. END \\n"
 "Q:[JOKE] \\n"
 "A:[PUNCHLINE] \\n"
FROM
   'openai/text-ada-001'
"""
    await lmql.run(query, output_writer=TestOutputWriter())


async def test_argmax_a_joke_with_constraints():
    query = """
argmax
 "A list of good dad jokes. A indicates the punchline \\n"
 "Q: How does a penguin build its house? \\n"
 "A: Igloos it together. END \\n"
 "Q: Which knight invented King Arthur's Round Table? \\n"
 "A: Sir Cumference. END \\n"
 "Q:[JOKE] \\n"
 "A:[PUNCHLINE] \\n"
FROM
   'openai/text-ada-001'
WHERE
   len(JOKE) < 120 and STOPS_AT(JOKE, "?") and 
   STOPS_AT(PUNCHLINE, "END") and len(PUNCHLINE) > 12
"""
    await lmql.run(query, output_writer=TestOutputWriter())

async def test_argmax_a_joke_with_constraints2():
    query = """
argmax
 "A list of good dad jokes. A indicates the punchline \\n"
 "Q: How does a penguin build its house? \\n"
 "A: Igloos it together. END \\n"
 "Q: Which knight invented King Arthur's Round Table? \\n"
 "A: Sir Cumference. END \\n"
 "Q:[JOKE] \\n"
 "A:[PUNCHLINE] another[ENDING] \\n"
FROM
 'openai/text-ada-001'
WHERE
 len(JOKE) < 120 and STOPS_AT(JOKE, "?") and 
 STOPS_AT(PUNCHLINE, "END") and 
 PUNCHLINE in [" A man has", "B"]
"""
    await lmql.run(query, output_writer=TestOutputWriter())


async def test_beam_var():
    query = """
beam_var
   "A list of good dad jokes. A indicates the punchline \\n"
   "Q: How does a penguin build its house? \\n"
   "A: Igloos it together. END \\n"
   "Q: Which knight invented King Arthur's Round Table? \\n"
   "A: Sir Cumference. END \\n"
   "Q:[JOKE] \\n"
   "A:[PUNCHLINE] another[ENDING] \\n"
FROM
   'openai/text-ada-001'
WHERE
   len(JOKE) < 120 and STOPS_AT(JOKE, "?") and 
   STOPS_AT(PUNCHLINE, "END") and 
   PUNCHLINE in [" A man has", "B"]
"""
    await lmql.run(query, output_writer=TestOutputWriter())


async def test_beam_var_hf():
    query = """
beam_var
   "A list of good dad jokes. A indicates the punchline \\n"
   "Q: How does a penguin build its house? \\n"
   "A: Igloos it together. END \\n"
   "Q: Which knight invented King Arthur's Round Table? \\n"
   "A: Sir Cumference. END \\n"
   "Q:[JOKE] \\n"
   "A:[PUNCHLINE] another[ENDING] \\n"
FROM
   'gpt2-medium'
WHERE
   len(JOKE) < 120 and STOPS_AT(JOKE, "?") and 
   STOPS_AT(PUNCHLINE, "END") and 
   PUNCHLINE in [" A man has", "B"]
"""
    await lmql.run(query, output_writer=TestOutputWriter())


async def main():
    # collect all method starting with test_ and run them
    for name, method in globals().items():
        if name.startswith("test_"):
            start = time.time()
            title = f"Running {name}"
            print(title.ljust(120, "."), end="", flush=True)
            await method()
            duration = time.time() - start
            print("(%.2fs)" % duration, " [OK]", flush=True)

asyncio.run(main())