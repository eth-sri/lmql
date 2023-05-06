# GPTSort snippet

```{lmql}
name::gptsort

@lmql.query
async def compare(a, b, criterion):
   '''
   argmax 
      """
      Q: On the scale of "{criterion}", how does "{a}" relate to "{b}" in terms of 
      being less or more (answer only with < or >):
      A: [RESULT]"""
      return RESULT
   from
      "openai/text-davinci-001"
   where
      RESULT in ["<", ">"]
   '''

argmax 
   data = [
      "I love you",
      "I am indifferent towards you",
      "I think it is complicated",
      "I hate you",
      "I like you",
   ]
   comparison_criterion = "how much someone likes you"

   result = [data[0]]
   # insertion sort (please forgive me)
   for d in data[1:]:
      if len(result) == 0:
         result = [d]
      for i in range(len(result)):
         cmp_result = (await compare(d, result[i], comparison_criterion))[0]
         if cmp_result == "<":
            break
      result.insert(i, d)
   print(result) # ['I hate you', 'I am indifferent towards you', 
   # 'I think it is complicated', 'I like you', 'I love you']
from 
   "openai/text-ada-001"
```

```{lmql}
name::mrkl
argmax
   """
   Answer the following questions as best you can. You have access to the following tools:

   Calculator: Useful for when you need to answer questions about math.

   Use the following format:

   Question: the input question you must answer
   Thought: you should always think about what to do
   Action: the action to take, should be one of {Calculator}
   Action Input: The input to the action (must be valid python)
   Observation: the result of the action
   ... (this Thought/Action/Action Input/Observation can repeat N times)
   Thought: I now know the final answer
   Final Answer: the final answer to the original input question

   Begin!

   Question: I have two apples and three friends, how many apples can I give each so it is fair?
   """
   for i in range(8):
      "[MODE]: [CONTENT]"
      if MODE.strip() == "Action":
         "Action Input: [ACTION_INPUT]"
         print("run action", CONTENT, "with input", ACTION_INPUT)
         "Observation: {eval(ACTION_INPUT)}\n"
from
   'openai/text-davinci-003'
where
   MODE in [" Thought", " Action", " Final Answer"] and STOPS_AT(CONTENT, "\n") and STOPS_AT(ACTION_INPUT, "\n")
```