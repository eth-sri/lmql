import lmql
import ast

from dataclasses import dataclass

async def wiki(q: str):
    """
    Searches Wikipedia for the provided term.
    
    Example: wiki("Basketball")
    Result: Basketball is a team sport in which two teams, most comm...
    """
    from lmql.http import fetch
    try:
        print("Searching for", [q], flush=True)
        q = q.strip("\n '.")
        pages = await fetch(f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&titles={q}&origin=*", "query.pages")
        return list(pages.values())[0]["extract"][:280]
    except:
        return "No results"

@dataclass
class LMQLActionFunction:
    name: str
    description: str
    example: str
    example_result: str
    fct: callable

    async def call(self, args):
        args = ast.literal_eval(args[:-len("#")].strip())
        if type(args) is tuple:
            return await lmql.lmql_runtime.call(self.fct, *args)
        else:
            return await lmql.lmql_runtime.call(self.fct, args)


def make_fct(f):
    docstring = f.__doc__
    return LMQLActionFunction(
        name=f.__name__,
        description=docstring.split("\n")[1].strip(),
        example=docstring.split("\n")[3].split("Example: ")[1],
        example_result=docstring.split("\n")[4].split("Result: ")[1],
        fct=f
    )

DELIMITER = "`"
DELIMITER_END = "`"

@lmql.query
async def expose(fcts):
    '''lmql
    incontext
        "{:system} Use tools before providing a definitive result. The tools available to you are:\n"
        
        action_fcts = {str(f.__name__): make_fct(f) for f in fcts}
        
        for fct in action_fcts.values():
            "- {DELIMITER}{fct.name.strip()}(...){DELIMITER_END}: {fct.description}. "
            "Usage: {DELIMITER}{fct.example} # {fct.example_result}{DELIMITER_END}\n"
        "Instruction: Always use delimiters {DELIMITER} and {DELIMITER_END} for tool invocations and interleave tools transparently, without explicitly mentioning them"
        "{:assistant} Thoughts and Tool Use:"
        truncated = ""
        while True:
            "[SEGMENT]"

            truncated += SEGMENT

            if not SEGMENT.endswith(DELIMITER):
                break
            else:
                "[CALL]"
                if not CALL.endswith("#"):
                    break
                else:
                    action, args = CALL.split("(", 1)
                    action = action.strip()
                    if action not in action_fcts.keys():
                        print("unknown action", [action], list(action_fcts.keys()))
                        " Unknown action: {action} {DELIMITER_END})"
                    else:
                        # try:
                        result = await action_fcts[action].call("(" + args)
                        " {result} {DELIMITER_END})"
                        # except Exception:
                        #     print("error executing action", ex)
                        #     " Error executing action {DELIMITER_END}"
                        #     continue
                    truncated = truncated[:-len(DELIMITER)] + "(used {})".format(action)
        "\n{:assistant} Final Response: [FINAL_RESPONSE]"
        return FINAL_RESPONSE
    where
        STOPS_AT(SEGMENT, DELIMITER) and STOPS_AT(CALL, "#")
    '''