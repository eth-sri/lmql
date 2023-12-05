import lmql

CONSTANT = 1

class Agent:
    def __init__(self):
        self.memory = ""
    
    @lmql.query
    async def interact(self, s: str, a=12):
        '''lmql
        argmax
            return s, a, self, CONSTANT
        from
            "chatgpt"
        '''

    def __str__(self):
        return f"Agent with memory: {self.memory}"

@lmql.query
async def positional_only(s: str):
    '''lmql
    argmax
        return s
    from
        "chatgpt"
    '''

@lmql.query
async def default_only(s: str = 'default'):
    '''lmql
    argmax
        return s
    from
        "chatgpt"
    '''

@lmql.query
async def positional_and_default(s: str, a: int = 12):
    '''lmql
    argmax
        return s, a
    from
        "chatgpt"
    '''

# function with CAPTURE
@lmql.query
async def capture(s: str):
    '''lmql
    argmax
        return s, CONSTANT
    from
        "chatgpt"
    '''

# multi kw default
@lmql.query
async def multi_kw_default(s: str = 'default', a: int = 12):
    '''lmql
    argmax
        return s, a
    from
        "chatgpt"
    '''

# multi kw with n>1 decoder
@lmql.query(model=lmql.model("random", seed=123))
async def multi_kw_multiplicity(s: str = 'default', a: int = 12):
    '''lmql
    sample(n=2)
    
    "Hi [COMPLETION]" where len(TOKENS(COMPLETION)) == 2
    return s, a
    '''

async def test_query_args():
    agent = Agent()
    
    input_value = "Hi there"
    a_value = 8 
    
    # method use in LC currently not supported
    # i = agent.interact.aschain()
    # s, a, ag, captured = (await i({"self": agent, "s": input_value, "CONSTANT": CONSTANT, "a": a_value}))[0]
    # assert s == input_value, f"Expected {input_value}, got {s}"
    # assert a == a_value, f"Expected {a_value}, got {a}"
    # assert ag == agent, f"Expected {agent}, got {a}"
    # assert captured == CONSTANT, f"Expected {CONSTANT}, got {captured}"

    # positional, keyword, self
    s, a, ag, captured = (await agent.interact(input_value, a=a_value, output_writer=lmql.stream("ANSWER")))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == a_value, f"Expected {a_value}, got {a}"
    assert ag == agent, f"Expected {agent}, got {a}"
    assert captured == CONSTANT, f"Expected {CONSTANT}, got {captured}"

    # positional, default, self
    s, a, ag, captured = (await agent.interact(input_value, output_writer=lmql.stream("ANSWER")))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == 12, f"Expected 12, got {a}"
    assert ag == agent, f"Expected {agent}, got {a}"
    assert captured == CONSTANT, f"Expected {CONSTANT}, got {captured}"

    # positional only
    s = (await positional_only(input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"

    # default only
    s = (await default_only())
    assert s == 'default', f"Expected 'default', got {s}"

    # kw only but set
    s = (await default_only(s=input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"

    # positional and default
    s, a = (await positional_and_default(input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == 12, f"Expected 12, got {a}"

    # multi kw default
    s, a = (await multi_kw_default())
    assert s == 'default', f"Expected 'default', got {s}"
    assert a == 12, f"Expected 12, got {a}"

    # multi kw default but set
    s, a = (await multi_kw_default(s=input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert a == 12, f"Expected 12, got {a}"

    # capture
    s, captured = (await capture(input_value))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert captured == CONSTANT, f"Expected {CONSTANT}, got {captured}"

    # capture with decoder n=2 (should be ignored)
    s, captured = (await capture(input_value, decoder="beam", n=2))
    assert s == input_value, f"Expected {input_value}, got {s}"
    assert captured == CONSTANT, f"Expected {CONSTANT}, got {captured}"

    # multi_kw_multiplicity
    results = (await multi_kw_multiplicity(s=input_value, a=a_value))
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    for s, a in results:
        assert s == input_value, f"Expected {input_value}, got {s}"
        assert a == a_value, f"Expected {a_value}, got {a}"

# multi kw default
@lmql.query
async def multi_kw_chain(s: str = 'default', a: int = 12):
    '''lmql
    argmax
        return {"result": (s, a)}
    from
        "chatgpt"
    '''

# multi kw default
@lmql.query
async def no_return_chain(s: str = 'default', a: int = 12):
    '''lmql
    argmax
        "This is [R1] and [R2]"
    from
        "chatgpt"
    where
        R1 == s and R2 == "8"
    '''