import lmql
from dataclasses import dataclass
from lmql.tests.expr_test_utils import run_all_tests

card_text = """\
Yktlash, the Unseen Empress

{3}{B}{B}{G}{G}
Legendary Creature â€” Elf Shaman (5/5)
Trample

When Yktlash, the Unseen Empress using the " character enters the battlefield, create three 1/1 black and green Elf Warrior creature tokens.

{B}{G}, Sacrifice an Elf: Target creature gets -3/-3 until end of turn.

> 'In the depths of the forest, her reign remains elusive. Only the echoes of her whispers reveal the true power she wields.'
"""

@dataclass
class CardData:
    name: str
    mana_cost: str
    supertypes: str
    types: str
    subtypes: str
    rules: str
    flavor: str
    # Creature
    attack: str
    defense: str
    # Planeswalker
    loyalty: str

@lmql.query(model="openai/gpt-3.5-turbo-instruct")
async def test_quote_and_nl():
    '''lmql
    "{card_text}\n"
    "Structured: [CARD_DATA]\n" where type(CARD_DATA) is CardData

    assert "\"" in CARD_DATA.rules, "Expected quotes to be preserved in 'rules', but got: " + str([CARD_DATA.rules])
    assert "\n" in CARD_DATA.rules, "Expected newline to be preserved in 'rules', but got: " + str([CARD_DATA.rules])
    '''

if __name__ == "__main__":
    run_all_tests(globals())