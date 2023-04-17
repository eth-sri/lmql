# Snippets LMQL Release 0.0.5

For full release notes, see the blog post.

Snippet on Postprocessing

```{lmql}

name::postprocessing-int-value
argmax
   "My favorite number is: [NUM]\n"
   print(type(NUM), NUM * 2) # <class 'int'> 4
   "Number times two is {NUM * 2}"
from
   'openai/text-ada-001'
where
   INT(NUM) 
```