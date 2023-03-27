module.exports = { queries: [
   
   {
      category: "Introductory Examples", 
      queries: [
         {
            // hello world
            name: "👋 Hello World",
            description: "Who This?",
            code: `argmax "Hello[WHO]" from "openai/text-ada-001" where len(WHO) < 10`,
            state: 'precomputed/hello.json'
         },
         {
            name: "👴 Tell A Joke",
            description: "Few-Shot Samples & Constraints",
            code: `argmax
   """A list of good dad jokes. A indicates the punchline
   Q: How does a penguin build its house?
   A: Igloos it together.
   Q: Which knight invented King Arthur's Round Table?
   A: Sir Cumference.
   Q:[JOKE]
   A:[PUNCHLINE]"""
from
   "openai/text-davinci-003"
where
   len(JOKE) < 120 and 
   STOPS_AT(JOKE, "?") and 
   STOPS_AT(PUNCHLINE, "\\n") and 
   len(PUNCHLINE) > 1`,
            state: 'precomputed/joke.json'
         },
         {
            name: "🌴 Packing List",
            description: "Control-Flow Guided Generation",
            code: `sample(temperature=0.8)
   "A list of things not to forget when going to the sea (not travelling): \\n"
   "- Sunglasses \\n"
   for i in range(4):
      "- [THING] \\n"
from
   'openai/text-ada-001'
where
   THING in set(["Volleyball", "Sunscreen", "Bathing Suite"])`,
            state: 'precomputed/list.json'
         },
      ]
   },
   {
      category: "LLM Reasoning", 
      queries: [
         {
            name: "🧠 Chain-Of-Thought",
            description: "CoT with robust result extraction.",
            code: `# zero-shot cot based on https://arxiv.org/pdf/2205.11916.pdf
argmax
   """Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?
   Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021
   A: Let's think step by step."""
   "[REASONING]\\n"
   "Therefore, among A through F, the answer is[RESULT]"
   assert RESULT == "A"
from
   "openai/text-davinci-003"
where
   RESULT in ["A", "B", "C", "D", "E", "F"]`,
            state: 'precomputed/cot.json'
         },
         {
            name: "👩‍🔬 Meta Prompting",
            description: "Asking an expert to answer.",
            code: `
# metaprompting based on https://arxiv.org/pdf/2102.07350.pdf
beam(n=2)
   "Q: What are Large Language Models?\\n\\n"
   "A good person to answer this question would be[EXPERT]\\n\\n"
   expert_name = EXPERT.rstrip(".\\n")
   "For instance,{expert_name} would answer[ANSWER]"
from 
   "openai/text-davinci-001"
where
   STOPS_AT(EXPERT, ".") and STOPS_AT(EXPERT, "\\n") and STOPS_AT(ANSWER, ".")`,
            state: 'precomputed/meta.json'
         },
      ]
   },
   {
      category: "Tool-Augmented Queries",
      queries: [
         {
            name: "🧮 Calculator",
            description: "On-the-fly arithmetic evaluation using Python.",
            code: `import re
from lmql.demo import gsm8k_samples

def calc(expr):
      expr = re.sub(r"[^0-9\+\\-*/\(\)\.]", "", expr)
      return eval(expr)

argmax(openai_chunksize=64, max_len=2048)
      QUESTION = "Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?"
      # few shot samples
      "{gsm8k_samples()}"
      # prompt template
      "Q: {QUESTION}\\n"
      "Let's think step by step.\\n"
      for i in range(4):
         "[REASON_OR_CALC]"
         if REASON_OR_CALC.endswith("<<"):
            " [EXPR]"
            " {calc(EXPR)}>>"
         elif REASON_OR_CALC.endswith("So the answer"):
            break
      "is[RESULT]"
from 
      'openai/text-davinci-003'
where
      STOPS_AT(REASON_OR_CALC, "<<") and
      STOPS_AT(EXPR, "=") and
      STOPS_AT(REASON_OR_CALC, "So the answer")`,
            state: 'precomputed/calc.json'
         },
         {
            name: "🌎 Wikipedia Search",
            description: "Interactive LM-driven Wikipedia search.",
            code: `async def wikipedia(q):
   from lmql.http import fetch
   try:
      q = q.strip("\\n '.")
      pages = await fetch(f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&titles={q}&origin=*", "query.pages")
      return list(pages.values())[0]["extract"][:280]
   except:
      return "No results"

argmax
   "Q: From which countries did the Norse originate?\\n"
   "Action: Let's search Wikipedia for the term '[TERM]\\n"
   result = await wikipedia(TERM)
   "Result: {result}\\n"
   "Final Answer:[ANSWER]"
from 
   "openai/text-davinci-003"
where
   STOPS_AT(TERM, "'")`,
            state: 'precomputed/wiki.json'
         },
         {
            name: "📖 Key-Value Memory",
            description: "Augment the LM with a key-value storage.",
            code: `# simple kv storage
storage = {}
def assign(key, value): storage[key] = value; return f'{{{key}: "{value}"}}'
def get(key): return storage.get(key)

argmax(n=1, openai_chunksize=128, max_len=2048, step_budget=4*2048)
   """In your reasoning you can use actions. You do this as follows:
   \`action_name(<args>) # result: <inserted result>\`
   To remember things, you can use 'assign'/'get':
   - To remember something:
   \`assign("Alice", "banana") # result: "banana"\`
   - To retrieve a stored value:
   \`get("Alice") # result: "banana"\`
   Always tail calls with " # result". Using these actions, let's solve the following question.
   
   Q: Alice, Bob, and Claire are playing a game. At the start of the game, they are each holding a ball: Alice has a black ball, Bob has a brown ball, and Claire has a blue ball. \\n\\nAs the game progresses, pairs of players trade balls. First, Bob and Claire swap balls. Then, Alice and Bob swap balls. Finally, Claire and Bob swap balls. At the end of the game, what ball does Alice have?
   A: Let's think step by step.\\n"""
   for i in range(32):
      "[REASONING]"
      if REASONING.endswith("# result"):
         cmd = REASONING.rsplit("\`",1)[-1]
         cmd = cmd[:-len("# result")]
         "{eval(cmd)}\`\\n"
      else:
         break
   """Therefore at the end of the game, Alice has the[OBJECT]"""
   assert "blue ball." in OBJECT
from 
   "openai/text-davinci-003"
where
   STOPS_AT(REASONING, "# result") and STOPS_AT(REASONING, "Therefore, ") and
   STOPS_AT(OBJECT, ".") and STOPS_AT(OBJECT, ",")            
`,
            state: 'precomputed/kv.json'
         }
      ]
   },
   {
      category: "Decoding",
      queries: [
         {
            name: "🔍 Visualize Decoding",
            description: "Inspect the decoding tree of beam search.",
            code: `beam(n=4)
   """English to French Translation:
   English: I am going to the store
   French: [TRANSLATION]
   """
from 
   "openai/text-davinci-001"
where
   STOPS_AT(TRANSLATION, "\\n")`,
            state: 'precomputed/translation.json'
         },
         {
            name: "📊 Conditional Distributions",
            description: "LM classification by conditional distributions.",
            code: `argmax
   """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.\\n
   Q: What is the underlying sentiment of this review and why?\\n
   A:[ANALYSIS]\\n
   Based on this, the overall sentiment of the message can be considered to be[CLASSIFICATION]"""
from 
   "openai/text-davinci-003"
distribution
   CLASSIFICATION in [" positive", " neutral", " negative"]`,
            state: 'precomputed/distribution.json'
         }
      ]
   },
   {
      category: "Chatbots",
      queries: [
         {
            name: "🗣️ Chatbot",
            description: "Build a chatbot using interaction querying.",
            code: `argmax 
   "{:system} You are a marketing chatbot for the language model query language (LMQL)."
   for i in range(10):
      "{:user} {await input()}"
      "{:assistant} [ANSWER]"
from
   "chatgpt"`,
            state: 'precomputed/chat.json'
         },
      ]
   },
]};