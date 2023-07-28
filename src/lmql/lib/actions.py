import lmql
import ast
from .prompts.wiki_prompt import EXAMPLES as WIKI_EXAMPLES
from .prompts.inline_use import INLINE_USE_PROMPT
from .prompts.inline_code import INLINE_CODE_PROMPT

from dataclasses import dataclass

async def wiki(q: str, lookup = None):
    """
    Searches Wikipedia (always use this for factual information).
    
    Example: wiki("Basketball")
    Result: Basketball is a team sport in which two teams, most comm...
    """
    from lmql.http import fetch
    try:
        print("Searching for", [q, lookup], flush=True)
        q = q.strip("\n '.")
        pages = await fetch(f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&titles={q}&origin=*", "query.pages")
        extract = list(pages.values())[0]["extract"][:280]
        return extract
    except:
        return "No results (try differently)"

async def calc(expr: str):
    """
    Evaluate the provided arithmetic expression in Python syntax.

    Example: calc("1+2*3")
    Result: 7
    """
    # in expr remove everything but numbers, operators, and brackets
    import re
    expr = str(expr)
    original_expr = expr
    expr = re.sub(r"[^0-9\+\-\*\/\(\)\.]", "", expr)

    expr = expr.strip("\n '")
    try:
        return eval(expr)
    except:
        return "Error. try differently, only use valid python without variables.".format(original_expr)
@dataclass
class LMQLActionFunction:
    name: str
    description: str
    example: str
    example_result: str
    fct: callable

    async def call(self, args):
        args = eval(args.strip())
        if type(args) is tuple:
            return await lmql.lmql_runtime.call(self.fct, *args)
        else:
            return await lmql.lmql_runtime.call(self.fct, args)


def make_fct(f):
    docstring = f.__doc__
    return LMQLActionFunction(
        name=f.__name__.strip(),
        description=docstring.split("\n")[1].strip(),
        example=docstring.split("\n")[3].split("Example: ")[1],
        example_result=docstring.split("\n")[4].split("Result: ")[1],
        fct=f
    )

DELIMITER = "<<"
DELIMITER_END = ">>"


@lmql.query
async def fct_call(fcts):
    '''lmql
    action_fcts = {str(f.__name__): make_fct(f) for f in fcts}
    "[CALL]" where STOPS_AT(CALL, "|") and STOPS_AT(CALL, DELIMITER_END)

    truncated = CALL
    if not CALL.endswith("|") and not CALL.endswith(DELIMITER_END):
        return CALL
    else:    
        if CALL.endswith(DELIMITER_END):
            CALL = CALL[:-len(DELIMITER_END)]
        else:
            CALL = CALL[:-len("|")]
        
        if "(" not in CALL:
            return CALL
        
        action, args = CALL.split("(", 1)
        action = action.strip()
        if action not in action_fcts.keys():
            print("unknown action", [action], list(action_fcts.keys()))
            " Unknown action: {action} {DELIMITER_END}"
            result = ""
            return "(error)"
        else:
            try:
                result = await action_fcts[action].call("(" + args.strip())
                return DELIMITER + str(CALL) + "| " + str(result)
            except Exception:
                result = "Error."
                return "(error)"
    '''


@lmql.query
async def inline_segment(fcts):
    '''lmql
    "[SEGMENT]" where STOPS_AT(SEGMENT, DELIMITER)
    if not SEGMENT.endswith(DELIMITER):
        return SEGMENT
    else:
        "[CALL]" where fct_call(CALL, fcts) and len(TOKENS(CALL)) > 0
        result = CALL.split("|", 1)[1]
        return SEGMENT[:-len(DELIMITER)] + CALL + DELIMITER_END
    '''

@lmql.query
async def inline_use(fcts, instruct=True):
    '''lmql
    action_fcts = {str(f.__name__): make_fct(f) for f in fcts}
    first_tool_name = list(action_fcts.keys())[0] if len(action_fcts) > 0 else "tool"

    # add instruction prompt if no few-shot prompt was already used
    if instruct and not INLINE_USE_PROMPT in context.prompt:
        """
        \n\nInstructions: In your reasoning, you can use the following tools:"""
        
        for fct in action_fcts.values():
            "\n   - {fct.name}: {fct.description} Usage: {DELIMITER}{fct.example} | {fct.example_result}{DELIMITER_END}"
        '   Example Use: ... this means they had <<calc("5-2") | 3 >> 3 apples left...\n'
        "   You can also use the tools multiple times in one reasoning step.\n\n"
        "Reasoning with Tools:\n\n"
    
    # decode segment-by-segment, handling action calls along the way
    truncated = ""
    while True: 
        "[SEGMENT]" where inline_segment(SEGMENT, fcts)
        if not SEGMENT.endswith(DELIMITER_END):
            " " # seems to be needed for now
            return truncated + SEGMENT
        truncated += SEGMENT
    return truncated
    '''
inline_use.demonstrations = INLINE_USE_PROMPT

def dedent(code):
    common_indent = None
    for line in code.split("\n"):
        if line.strip() == "":
            continue
        if common_indent is None:
            common_indent = line[:len(line) - len(line.lstrip())]
        else:
            common_indent = min(common_indent, line[:len(line) - len(line.lstrip())])
    if common_indent is None:
        return code
    else:
        return "\n".join([line[len(common_indent):] for line in code.split("\n")])

async def exec_or_timeout(SEGMENT, code_env):
    import asyncio

    if dedent(SEGMENT).strip() == "":
        return

    try:
        async def wrapper():
            return exec(dedent(SEGMENT), code_env, code_env)
        return await asyncio.wait_for(wrapper(), timeout=1)
    except Exception as e:
        print("error executing", SEGMENT, e)
        raise e

async def eval_or_timeout(SEGMENT, code_env):
    import asyncio

    if dedent(SEGMENT).strip() == "":
        return

    try:
        async def wrapper():
            return eval(dedent(SEGMENT), code_env, code_env)
        return await asyncio.wait_for(wrapper(), timeout=1)
    except Exception as e:
        print("error evaluating", SEGMENT, e)
        raise e

@lmql.query
async def exec_code():
    '''lmql
    import asyncio

    incontext
        if INLINE_CODE_PROMPT not in context.prompt:
            "```\n"
            "# step by step solution in Python (a solution() function that returns the result)\n"
            "def solution():\n"
        else:
            "# solution in Python:\n"
            "\n\n\ndef solution():\n"
        truncated = "\n"
        code_env = {}
        num_errors = 0
        # carry over incomplete lines of code for eval
        acc = None

        while True:
            "[SEGMENT]"

            truncated += SEGMENT

            if truncated.count("# None") > 2:
                break
            if SEGMENT.strip() == "":
                " \n"
                continue

            if SEGMENT.endswith("```"):
                break
            else:
                try:
                    if not "return " in SEGMENT:
                        exec_or_timeout(SEGMENT, code_env)
                except:
                    print("Failed to run code", [SEGMENT])
                    num_errors += 1
                # check for variable assignment
                last_line = SEGMENT
                if "return " in last_line:
                    return_expr = last_line.split("return ", 1)[-1]
                    try:
                        value = eval_or_timeout(return_expr, code_env)
                        " #| {value}\n"
                        truncated += " #| " + str(value) + "\n"
                        break
                    except:
                        num_errors += 1
                        " #| error\n"
                        truncated += "# error\n"
                        break
                elif "=" in last_line:
                    value = last_line.split("=")[1].strip()
                    
                    value, acc = await eval_or_acc(value, code_env, acc)
                    if value in last_line:
                        value = ""
                    
                    if len(value.strip()) == 0:
                        " \n"
                        truncated += " \n"
                    else:
                        "#| {value}\n"
                        truncated += "#| " + str(value) + "\n"
                elif "print(" in last_line:
                    expr = last_line.split("print(")[-1].split(")")[0]
                    try:
                        value = eval_or_timeout(expr, code_env)
                        " #| {value}\n"
                        truncated += " #| " + str(value) + "\n"
                    except:
                        num_errors += 1
                        " #| error\n"
                        truncated += "# error\n"
                elif "solution()" in last_line:
                    try:
                        value = eval_or_timeout("solution()", code_env)
                        print("evaluates to ", [value])
                        " #| {value}\n"
                        truncated += " #| " + str(value) + "\n"
                        break
                    except:
                        num_errors += 1
                        "# error\n"
                        truncated += "# error\n"
                        break
                else:
                    value, acc = await eval_or_acc(last_line, code_env, acc)
                    if len(value.strip()) == 0:
                        " \n"
                        truncated += " \n"
                    else:
                        "# {value}\n"
                        truncated += "# " + str(value) + "\n"
        return truncated
    where
        STOPS_BEFORE(SEGMENT, "#|") and STOPS_BEFORE(SEGMENT, "\n") and STOPS_AT(SEGMENT, "```") and len(TOKENS(SEGMENT)) < 32
    '''
exec_code.demonstrations = INLINE_CODE_PROMPT

async def eval_or_acc(last_line, code_env, acc):
    try:
        if acc is not None:
            last_line = acc + last_line
        value = await eval_or_timeout(last_line, code_env)
        if last_line.endswith('"""'):
            return "", None
        return str(value), None
    except Exception as e:
        if "unmatched" in str(e) or "never closed" in str(e) or "unterminated" in str(e):
            acc = last_line
            return "", acc
        return "", None

@lmql.query
async def reAct(fcts, instruct=True):
    '''lmql
    if instruct:
        """
        Instructions: In your reasoning adhere to the following structure:

            Thought: <your conclusions>
            
            If required you can also use the following actions:
                Action: tool(<ARG>)
                Observation: <TOOL OUTPUT>
        
            Available Tools:
        """
        action_fcts = {str(f.__name__): make_fct(f) for f in fcts}
        
        for fct in action_fcts.values():
            "   - {fct.name}: {fct.description}. Usage: {fct.example}. Observation: {fct.example_result}\n"
    
        "Now you can start reasoning.\n"
        
    offset = len(context.prompt)
    
    while True:
        "[SEGMENT]" where STOPS_AT(SEGMENT, "Action:")

        if not SEGMENT.endswith("Action:"):
            break
        else:
            "[CALL]" where STOPS_AT(CALL, "\n")
            
            if not CALL.endswith("\n") or not "(" in CALL:
                continue
            else:
                "Observation:"
                action, args = CALL.split("(", 1)
                action = action.strip()
                if action not in action_fcts.keys():
                    print("unknown action", [action], list(action_fcts.keys()))
                    " Unknown action: {action}\n"
                    result = ""
                else:
                    try:
                        result = await action_fcts[action].call("(" + args)
                        if type(result) is float:
                            result = round(result, 2)
                        " {result}\n"
                    except Exception:
                        " Error. Try differently.\n"
    
    return "\n" + context.prompt[offset:]
    '''


if __name__ == "__main__":
    code = ' eggs_per_day = 16\n    eggs_eaten = 3\n    eggs_baked = 4933828\n    egg_price = 2\n   \n   money_made = (eggs_per_day - eggs_eaten - eggs_baked) * egg_price #|'
    print(dedent(code))
    print(exec(dedent(code)))