import lmql

# llm: lmql.LLM = lmql.model("openai/text-ada-001")

if __name__ == "__main__":
    # greet = lmql.F("Hello[WHO]", model=llm, constraints="len(TOKENS(WHO)) < 10")
    # print(greet().strip())
    # print(llm.generate_sync("Hello", max_tokens=10).strip())
    r = lmql.score_sync("Hello", [" There", " World", " Earth", " Universe", ", how are you"], model="local:gpt2")
    print(r)
    print(r.argmax())
