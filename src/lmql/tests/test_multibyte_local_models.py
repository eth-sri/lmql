import lmql
from lmql.tests.expr_test_utils import run_all_tests

m = lmql.model("local:gpt2", cuda=True)

@lmql.query
async def test_special_characters1():
    '''lmql
    argmax
        """French: Sonde V18, Ø18 x 85mm, 33kHz, 8m, raccord ressort & taraudé M12, livré avec 2 piles 3.6V LS14250
        French:[REPEAT] Ø [REP2]
        """
        assert REPEAT.count("Ø") == 1, "REPEAT should contain Ø once"
        assert context.prompt.count("Ø") >= 3, "Ø should occur at least 3 times in full prompt"
    from
        m
    where
        len(TOKENS(REPEAT)) < 10 and len(TOKENS(REP2)) < 10
    '''

@lmql.query
async def test_special_characters_pi():
    '''lmql
    argmax
        """A circle has a radius of 3cm. What is the Area? The area of a circle is computed with the following formula: A = πr2. Therefore, the area of the circle with a radius of 3cm is 28.27 cm2.
        Repeat: A circle has a radius of 3cm. What is the Area? The area[formula]
        """
        assert "π" in formula, "π must occur in the formula"
    from
        m
    where
        len(TOKENS(formula)) < 20
    '''

if __name__ == "__main__":
    run_all_tests(globals())