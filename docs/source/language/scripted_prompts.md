# Scripted Prompting

In LMQL, prompts are not just static text, but can also contain control flow (e.g. loops, conditions, function calls). This facilitates dynamic prompt construction, but also allows LMQL queries to respond dynamically to intermediate model output. 

For instance, consider the following LMQL query:

```{lmql}
  
name:: hello-lmql
argmax "Hello[WHO]" from "openai/text-ada-001" WHERE len(WHO) < 10
```