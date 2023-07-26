export const queries = {
    queries: [

        {
            category: "Introductory Examples",
            queries: [
                {
                    name: "🛠️ Inline Tool Use",
                    description: "Few-Shot Samples & Constraints",
                    code: `
def wiki(q: str): 
    """
    Searches Wikipedia (always use this for factual information).

    Example: wiki("Basketball")
    Result: Basketball is a team sport in which two ...
    """
    ...
def calc(expr: str): 
    """
    Evaluate the provided arithmetic expression in Python syntax.

    Example: calc("1+2*3")
    Result: 7
    """
    ...

@lmql.query
def chatbot_query():
    "Q: What is the population of the US and Germany combined?"
    "Let's think step by step"

    "A: [REASONING]" where 
        ➥ inline_use(REASONING, [wiki, calc])

    "Therefore the answer is[ANSWER]" where INT(ANSWER)
`,
                    state: 'precomputed/simple-chat.json'
                }, 
                {
                    name: "📃 ReAct Reasoning",
                    description: "ReAct Reasoning",
                    code: `from lmql.lib.actions import reAct, calc, wiki

"Q: What is two times the birth year of Michele Obama?"
"A: Let's think step by step\\n"

"[REASONING]\\n" where reAct(REASONING, [wiki, calc])

# determine final response, after reasoning finishes
"Therefore the answer is[ANSWER]" where INT(ANSWER)`,
                    state: 'precomputed/react-reasoning.json'
                },
                {
                    name: "💻 Code Interpreter",
                    description: "Code Interpreter",
                    code: `from lmql.lib.actions import exec_code

"Q: What the square root of 123123 - 19?"
"A: Let's think step by step"

"[REASONING]" where exec_code(REASONING)

"Therefore the answer is[ANSWER]"`,
                    state: 'precomputed/code-interpreter.json'
                }
            ]
        },
    ]
}