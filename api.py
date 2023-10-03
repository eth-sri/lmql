import lmql

m = lmql.model("openai/gpt-3.5-turbo-instruct")

# simple generation
m.generate_sync("Hello", max_tokens=10)
# Hello, I am a 23 year old female.

# sequence scoring
m.score_sync("Hello", ["World", "Apples", "Oranges"])
# lmql.ScoringResult(model='openai/gpt-3.5-turbo-instruct')
# -World: -3.9417848587036133
# -Apples: -15.26676321029663
# -Oranges: -16.22640037536621