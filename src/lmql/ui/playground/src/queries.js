module.exports = { queries: [
   
   {
      category: "Introductory Examples", 
      queries: [
         {
            // hello world
            name: "👋 Hello World",
            description: "Who This?",
            code: `"Say 'this is a test':[RESPONSE]" where len(TOKENS(RESPONSE)) < 10`,
            state: 'precomputed/hello.json'
         },
         {
            name: "👴 Tell A Joke",
            description: "Few-Shot Samples & Constraints",
            code: `\
# instructions + few-shot samples
"""
A list of good dad jokes. A indicates the punchline
Q: How does a penguin build its house?
A: Igloos it together.
Q: Which knight invented King Arthur's Round Table?
A: Sir Cumference.
"""

# generate a joke
"Q:[JOKE]\\n" where len(TOKENS(JOKE)) < 120 and STOPS_AT(JOKE, "?")
"A:[PUNCHLINE]" where STOPS_AT(PUNCHLINE, "\\n") and len(TOKENS(PUNCHLINE)) > 1`,
            state: 'precomputed/joke.json'
         },
         {
            name: "🌴 Packing List",
            description: "Control-Flow Guided Generation",
            code: `# specify a decoding strategy for the query
sample(temperature=0.8)

"A list of things not to forget when going to the beach: \\n"
# use a loop to generate a list
for i in range(4):
    "- [THING] \\n" where \\
        THING in set(["Volleyball", "Sunscreen", "Bathing Suit"])`,
            state: 'precomputed/list.json'
         },
         {
            name: "📝 Templates",
            description: "Template-Based Generation for JSON data",
            code: `\
"""
Write a summary of Bruno Mars, the singer:
{{
    "name": "[STRING_VALUE]",
    "age": [INT_VALUE],
    "top_songs": [[
        "[STRING_VALUE]",
        "[STRING_VALUE]"
    ]]
}}
""" where STOPS_BEFORE(STRING_VALUE, '"') and \\
          INT(INT_VALUE) and len(TOKENS(INT_VALUE)) < 2`,
            state: 'precomputed/json-template.json'
         }
      ]
   },
   {
    category: "Features In Preview", 
    highlight: true,
    queries: [
       {
          // hello world
          name: "👨‍👩‍👧 Types / JSON",
          description: "Generate schema-safe, typed data.",
          code: `import lmql
from dataclasses import dataclass

@dataclass
class Employer:
    employer_name: str
    location: str

@dataclass
class Person:
    name: str
    age: int
    employer: Employer
    job: str

# use type constraints to generated (type-safe) structured data
"Alice is a 21 years old and works as an engineer at LMQL Inc in Zurich, Switzerland.\\n"
"Structured: [PERSON_DATA]\\n" where type(PERSON_DATA) is Person

# the resulting object is directly accessible as a Python object
"Their name is {PERSON_DATA.name} and she works in {PERSON_DATA.employer.location}."`,
          state: 'precomputed/json-robust.json'
       },
       {
          name: "🛠️ Multi-Tool Use",
          description: "Simply expose Python functions as LLM tools.",
          code: `from lmql.lib.actions import inline_use, calc, wiki

"Q: What is the population of the US and Germany combined?\\n"
"A: Let's consider the latest information to compute an answer\\n"

# expose Python functions as LLM tools
"[REASONING]\\n" where inline_use(REASONING, [wiki, calc])

# use an integer-typed variable to extract the final result
"Therefore the answer is[ANSWER: int]"`,
            state: ''
       },
       {
          name: "🔤 Regex Constraints",
          description: "Specify constraints using regex.",
          code: `# to structure output, you can enforce regex expressions
"It's the last day of June so today (DD/MM) is [RESPONSE: r'[0-9]{2}/[0-9]{1,2}']"`,
            state: 'precomputed/date-regex.json'
       },
       {
          // hello world
          name: "❤️ Sentiment Constraints",
          description: "Affect sentiment with in-context instructions.",
          code: `# uses nested queries to generate sentiment-guided chatbot responses 
# see https://lmql.ai/docs/language/nestedqueries.html to learn more about nested queries

# sub-query to generate ad-hoc instructions to match a specific mood
@lmql.query(cache="mood.tokens", model="chatgpt")
async def mood_description(m: str):
    '''lmql
    print("Generating mood for", m)
    """Provide a one sentence instruction that prompts a model to write text that 
    is written in a {m} tone, addressing some previously provided question.\\n"""
    "[SUMMARY]\\n"
    return SUMMARY.strip();
    '''

# nested query to instruct the model answer matching a given mood
@lmql.query
async def mood(m: str):
    '''lmql
    """
    Instruction: {await mood_description(m)}
    Answer: [RESPONSE]
    """ where stops_at(RESPONSE, ".") and stops_at(RESPONSE, "\\n")

    return RESPONSE.strip(); 
    '''


# main query (e.g. a chabot conversation)
argmax
    for q in ["Hi", "Who are you", "How is your day going?"]:
        "Q: {q}\\n"
        # replace the above with "Q: {await input()}\\n" to enable interactive chatting
        "A: [RESPONSE]\\n" where mood(RESPONSE, "loving like a partner")
from
    "chatgpt"`,
          state: ''
       },
       {
          // hello world
          name: "📝 Write A Poem",
          description: "Insert dynamic instructions during generation.",
          code: `# nested query to generate a rhyme for the previous line
@lmql.query
async def rhyme():
    '''
    """
    Instruction: Above is the beginning of the poem. Generate the next verse that rhymes with the last line and has the same number of syllables:
    Response:[VERSE]
    """ where stops_before(VERSE, "\\n")
    return VERSE
    '''

# nested query to generate the first line of our poem
@lmql.query
async def first_verse():
    '''
    """
    Instruction: Generate a verse that would be a good first line of a poem.
    Response:[VERSE]
    """ where not "\\n" in VERSE
    return VERSE
    '''

# vary the poem
sample(temperature=0.7)

# set the topic
"A poem on large language models:\\n"

# generate a poem using nested queries
"[FIRST_VERSE: first_verse]\\n"
for i in range(5):
    "[VERSE: rhyme]\\n"`,
          state: ''
       }
    ]
 },
   {
      category: "LLM Reasoning", 
      queries: [
         {
            name: "🧠 Chain-Of-Thought",
            description: "CoT with robust result extraction.",
            code: `"""Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?
Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021
"""

# chain-of-thought instruction
"A: Let's think step by step.\\n"

# free-form reasoning
"[REASONING]\\n"

# constrain the final answer to robustly extract the result
"Therefore, among A through F, the answer is[RESULT]" where \\
    RESULT in ["A", "B", "C", "D", "E", "F"]`,
            state: 'precomputed/cot.json'
         },
         {
            name: "👩‍🔬 Meta Prompting",
            description: "Asking an expert to answer.",
            code: `# use beam search to explore different potential 'expert' values
beam(n=2)
    "Q: What are Large Language Models?\\n\\n"

    # prompt for an 'expert'
    "A good person to answer this question would be[EXPERT]\\n\\n" where \\
        STOPS_AT(EXPERT, ".") and STOPS_AT(EXPERT, "\\n")
    expert_name = EXPERT.rstrip(".\\n")

    # use 'expert' to answer the question
    "For instance,{expert_name} would answer[ANSWER]" where STOPS_AT(ANSWER, ".")
from
    "openai/text-davinci-003"`,
            state: 'precomputed/meta.json'
         }
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
    expr = re.sub(r"[^0-9+\\-*/().]", "", expr)
    return eval(expr)

QUESTION = "Josh decides to try flipping a house. \\
He buys a house for $80,000 and then puts in $50,000 in repairs. \\
This increased the value of the house by 150%. \\
How much profit did he make?"

# insert few shot demonstrations
"{gsm8k_samples()}"

# prompt template
"Q: {QUESTION}\\n"
"Let's think step by step.\\n"

# reasoning loop
for i in range(4):
    "[REASON_OR_CALC]" \\
        where STOPS_AT(REASON_OR_CALC, "<<") and \\
                STOPS_AT(REASON_OR_CALC, "So the answer")
    
    if REASON_OR_CALC.endswith("<<"):
        " [EXPR]" where STOPS_AT(EXPR, "=")
        # invoke calculator function
        " {calc(EXPR)}>>"
    elif REASON_OR_CALC.endswith("So the answer"):
        break

# produce the final answer
"is[RESULT]"`,
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
        return list(pages.values())[0]["extract"][:190]
    except:
        return "No results"

"Q: From which countries did the Norse originate?\\n"
"Action: Let's search Wikipedia for the term '[TERM]\\n" where STOPS_AT(TERM, "\\n")
result = await wikipedia(TERM)
"Result: {result}\\n"
"Final Answer:[ANSWER]"`,
            state: 'precomputed/wiki.json'
         },
         {
            name: "📖 Key-Value Memory",
            description: "Augment the LM with a key-value storage.",
            code: `# implement a simple key value storage
# with two operations
storage = {}
def assign(key, value): 
    # store a value
    storage[key] = value; return f'{{{key}: "{value}"}}'
def get(key): 
    # retrieve a value
    return storage.get(key)

# instructive prompt, instructing the model to how use the storage
"""In your reasoning you can use actions. You do this as follows:
\`action_name(<args>) # result: <inserted result>\`
To remember things, you can use 'assign'/'get':
- To remember something:
\`assign("Alice", "banana") # result: "banana"\`
- To retrieve a stored value:
\`get("Alice") # result: "banana"\`
Always tail calls with " # result". Using these actions, let's solve the following question.\\n"""

# actual problem statement
"""
Q: Alice, Bob, and Claire are playing a game. At the start 
of the game, they are each holding a ball: Alice has a black 
ball, Bob has a brown ball, and Claire has a blue ball. 

As the game progresses, pairs of players trade balls. First, 
Bob and Claire swap balls. Then, Alice and Bob swap balls. 
Finally, Claire and Bob swap balls. At the end of the game, 
what ball does Alice have?
A: Let's think step by step.
"""

# core reasoning loop
for i in range(32):
    "[REASONING]" where STOPS_AT(REASONING, "# result") and \\
                        STOPS_BEFORE(REASONING, "Therefore,")
    
    if REASONING.endswith("# result"):
        cmd = REASONING.rsplit("\`",1)[-1]
        cmd = cmd[:-len("# result")]
        "{eval(cmd)}\`\\n"
    else:
        break

# generate final answer
"Therefore at the end of the game, Alice has the[OBJECT]" \\
    where STOPS_AT(OBJECT, ".") and STOPS_AT(OBJECT, ",")`,
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
            code: `# beam search explore multiple alternative decoding options
# to inspect the tree of explored sequences, make sure to open the 'Advanced Mode'
# in the LMQL Playground
beam(n=4)
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
            name: "📊 Distributions",
            description: "Classification via LM-based conditional distributions.",
            code: `argmax
    """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.\\n
    Q: What is the underlying sentiment of this review and why?\\n
    A:[ANALYSIS]
    """
    "Based on this, the overall sentiment of the message \\
        can be considered to be[CLASSIFICATION]" distribution \\
        CLASSIFICATION in [" positive", " neutral", " negative"]
    
    # Output:
    # P(CLASSIFICATION)
    # -  positive (*) 0.9997506492815857
    # -  neutral      0.0002479301558564076
    # -  negative     1.4205625578758162e-06
from 
    "openai/text-davinci-003"`,
            state: 'precomputed/distribution.json'
         }
      ]
   },
   {
      category: "Chatbots",
      requires_input: true,
      queries: [
         {
            name: "🗣️ Chatbot",
            description: "Build a chatbot using interactive querying.",
            code: `argmax 
    # use tags like {:system} to mark prompt segments as system/user/assistant
    "{:system} You are a marketing chatbot for the language model query language (LMQL)."
    for i in range(10):
        # use 'await input()' to interactive query for user input
        "{:user} {await input()}"
        "{:assistant} [ANSWER]"
from
    "chatgpt"`,
            state: 'precomputed/chat.json'
         },
      ]
   },
]};
