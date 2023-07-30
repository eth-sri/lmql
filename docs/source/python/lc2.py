from lmql.runtime.langchain.llm import LMQL as LMQL_LLM

lmql_llm = LMQL_LLM(
    model="llama.cpp:airoboros-7b-gpt4-1.4.ggmlv3.q4_K_S.bin",
)

print(lmql_llm(
    "## Intro: The",
    stop=["\n", "."],
    temperature=0.9,
    max_length = 20,
))