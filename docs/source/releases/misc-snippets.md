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