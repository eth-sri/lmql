export const queries = {
    queries: [

        {
            category: "Introductory Examples",
            queries: [
                {
                    name: "💬 Simple Chat Flow",
                    description: "Few-Shot Samples & Constraints",
                    code: `
def calc(expr: str): ...
def wiki(q: str): ...

"Q: What is the population of the US and Germany combined?\\n"
"A: Let's think step by step\\n"

"[REASONING]\\n" where inline_use(REASONING, [wiki, calc])

"Therefore the answer is[ANSWER]" where INT(ANSWER)`,
                    state: 'precomputed/joke.json'
                },
            ]
        }
    ]
}