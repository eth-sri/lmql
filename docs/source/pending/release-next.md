metadata:release: 2023-05-12 18:00:00 +0000
metadata:authors: team

# Introducing LMQL Next

Today we are announcing **LMQL Next**, our preview release channel for LMQL, allowing us to ship the latest features to the community and get feedback, while also maintaining a stable release channel for more stable use on `main`. 

LMQL Next is continously deployed and can be used starting today, via <a href="https://next.lmql.ai">https://next.lmql.ai</a> or locally by installing LMQL directly from the corresponding branch: `pip install git+https://github.com/eth-sri/lmql@next`. We encourage everyone to try Next, and share feedback with us via [GitHub](https://github.com/eth-sri/lmql) or our [Discord community](https://discord.gg/7eJP4fcyNT).

As part of **LMQL Next**, as we launch it today, we are excited to share **two major upcoming features** with the community, that will soon also land on `main`.

## LMQL Type Constraints

Extracting structured data from LLMs remains one of the biggest challenges in LM programming. Even though LLMs are powerful reasoners, generating structured data that corresponds to a given schema is still very difficult.

LMQL is uniquely positioned to solve this problem, as its constraints are enforced strictly on the output of a language model, meaning that the output of LMQL is guaranteed to be of a specified format and does not rely on the success of unreliable prompting strategies.

For this reason, we are excited to introduce **LMQL Type Constraints, a native language feature that allows users to easily specify structure and desired type of LLM output in a *single line of LMQL***, without the need to write any custom parsing, validation or type-checking code. 

To illustrate, consider the following example, in which we generate a `Person` object using LMQL type constraints:

```{lmql}
name::next-type-constraints
import lmql
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

argmax
    "Alice is a 21 years old and works as an engineer at LMQL Inc in Zurich, Switzerland: [p]\n"
    "The name is {p.name} and she works in {p.employer.location}."
from 
    "chatgpt" 
where 
    type(p) is Person
```

Because of the type constraint `type(p) is Person`, LMQL will automatically impose type-dependent masking during text generation, such that the resulting value of `p` will always be an LLM-generated, valid and already-converted instance of the `Person` class. After generating a `Person` object `p`, we can easily access different object attributes like `p.employer.location`, without any further need for parsing or validation.

**Full Efficiency**: Type constraints are implemented as a two-level generation process. First, LMQL calls the model in an unrestricted way, to generate a candidate value for `p`. If `p` already satisfies the type constraint, the candidate is returned, costing users exactly one request. In case the LLM fails to fully respect the provided schema, LMQL will step the model through the provided object hierarchy, making sure all object attributes are filled with valid values. This two level generation process ensures that with LMQL, users get the best possible performance if the LLM is correct on the first try, while also guaranteeing that the output is always a valid instance of the specified type, by applying scripted and constrained generation as a fallback with guranateed success.



## LMQL In-Context Functions