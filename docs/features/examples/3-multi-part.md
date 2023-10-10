---
title: 🧠 Multi-Part Prompts
---

LMQL's programming model supports multi-part prompt programs, enabling enhanced controls over the LLM reasoning process.

%SPLIT%
```lmql
# use multi-part prompting for complicated questions
"Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?"
"Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021"

# use a reasoning step to break down the problem
"A: Let's think step by step.\n [REASONING]"

# use a constrained variable to extract the final response
"Therefore, the answer is [ANSWER]" where \
    ANSWER in ["A", "B", "C", "D", "E", "F"]

# access results just like a normal variable
ANSWER # "A"
```
%SPLIT%
```promptdown
Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?
Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021

A: Let's think step by step.
[REASONING(color='red')| Sept. 1st, 2021 was a week ago, so 10 days ago would be 8 days before that, which is August 23rd, 2021, so the answer is (A) 08/29/2021.]

Therefore, the answer is [ANSWER| A]
```