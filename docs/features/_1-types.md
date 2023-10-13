---
title: Typed LLMs
template: side-by-side
new: true
---

To make language model interaction more robust, LMQL provides typed output.<br/><br/>

Any output <code>[VARIABLE]</code> can be annotated with a type, and LMQL will ensure that the output is valid by enforcing inference constraints.

<button class="btn">
Learn more
</button>

%SPLIT%
```lmql
@dataclass
class Person:
    name: str
    age: int
    job: str

"""
Alice is [AGE] years old and has a GPA of [GPA: float].
She works at [COMPANY: str] as a [JOB: str] in [CITY: str].
To summarize, Alice is a [p: Person].
"""
p.name # Alice
```