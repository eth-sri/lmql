---
title: 🌳 Meta Prompting
---

LMQL supports *program-level* decoding algorithms like `beam`, `sample` and `best_k`, allowing for a branching exploration of multi-step reasoning flows.

%SPLIT%
```lmql
# specify a decoding algorithm (e.g. beam, sample, best_k)
# to enable multi-branch exploration of your program
beam(n=2)

# pose a question
"Q: What are Large Language Models?\n\n"

# use multi-part meta prompting for improved reasoning
"A good person to answer this question would be[EXPERT]\n\n" where STOPS_AT(EXPERT, ".") and STOPS_AT(EXPERT, "\n")

# process intermediate results in Python
expert_name = EXPERT.rstrip(".\n")

# generate the final response by leveraging the expert
"For instance,{expert_name} would answer [ANSWER]" \ 
    where STOPS_AT(ANSWER, ".") 
```
%SPLIT%
```promptdown
Q: What are Large Language Models?⏎

A good person to answer this question would be [EXPERT| a data scientist or a machine learning engineer.]

For instance, (a data scientist or a machine learning engineer) would answer [ANSWER| this question by explaining that large language models are a type of artificial intelligence (AI) model that uses deep learning algorithms to process large amounts of natural language data.]
```