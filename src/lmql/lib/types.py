import lmql
import json
from dataclasses import dataclass, fields, is_dataclass
from typing import List

global is_oneshot
is_oneshot = True

def type_schema(t):
    if is_dataclass(t):
        return {f.name: type_schema(f.type) for f in fields(t)}
    elif t is int:
        return int
    elif t is str:
        return str
    elif hasattr(t, "__origin__") and t.__origin__ is list:
        element_type = t.__args__[0]
        return [type_schema(element_type)]
    else:
        assert False, "not a supported type " + str(t)

def type_schema_description(t):
    s = type_schema(t)
    return inner_schema_example(s)

def inner_schema_example(s):
    if s is int:
        return "21 // just an integer"
    elif s is str:
        return "\"hello\" // just a string"
    elif type(s) is list:
        return "[\n" + inner_schema_example(s[0]) + "\n..." + "\n] // a list of the above"
    elif type(s) is dict:
        return "{\n" + ",\n".join([f"\"{k}\": {inner_schema_example(v)}" for k, v in s.items()]) + "\n} // an object with the above fields"

def type_dict_to_type_instance(data, t):
    if is_dataclass(t):
        return t(**{f.name: type_dict_to_type_instance(data[f.name], f.type) for f in fields(t)})
    elif t is int:
        return int(data)
    elif t is str:
        return str(data)
    elif hasattr(t, "__origin__") and t.__origin__ is list:
        element_type = t.__args__[0]
        return [type_dict_to_type_instance(d, element_type) for d in data]
    else:
        assert False, "not a supported type " + str(t)

def oneshot(state):
    global is_oneshot
    is_oneshot = state

def extract_json(s):
    stack = []
    start = -1
    for i, c in enumerate(s):
        if len(stack) == 0 or stack[-1] != '"':
            if c == "{":
                start = i if start == -1 else start
                stack.append("{")
            elif c == "}":
                assert stack.pop() == "{"
            elif c == "[":
                start = i if start == -1 else start
                stack.append("[")
            elif c == "]":
                assert stack.pop() == "["
            elif c == '"':
                if len(stack) > 0 and stack[-1] == '"':
                    stack.pop()
                else:
                    stack.append('"')
        else:
            if c == '"':
                stack.pop()
        if len(stack) == 0 and start != -1:
                return s[start:i+1]
    return s

@lmql.query
async def single_shot_as_type(s, ty, model="chatgpt"):
    '''lmql
    argmax(openai_chunksize=1024)
        schema_description = type_schema_description(ty)
        "Provided a data schema of the following schema: {schema_description}\n"
        "Translate the following into a JSON payload: {s}\n"
        "JSON: [JSON]"
        e = extract_json(JSON)
        return e
    from 
        model
    '''

@lmql.query
async def is_type(ty, description=False):
    '''lmql
    if is_oneshot and "openai/" in context.interpreter.model_identifier:
        # "oneshot type prediction is only needed with openai/ models"
        # first run a simple one-shot query to get an initial result
        simple_json_result = single_shot_as_type(context.prompt, ty, model=context.interpreter.model_identifier)
        try:
            already_parsed = json.loads(simple_json_result)
        except Exception as e:
            print("Failed to parse JSON result from one-shot query: ", e, [simple_json_result])
            already_parsed = {}
    else:
        already_parsed = {}
    
    # then do scripted parsing as a fallback (does not query the model if already_parsed already contains all the keys we need)
    if description:
        "JSON Format:"
        "{type_schema_description(ty)}\n"
    "As JSON: "
    schema = type_schema(ty)
    stack = [("", "top-level", schema, already_parsed)]
    indent = ""
    while len(stack) > 0:
        t = stack.pop(0)
        if type(t) is tuple:
            k = t[0]
            element_type = t[1]
            key_type = t[2]
            
            existing_value = t[3]
            existing_list = t[3]
            index = 0
            if element_type == "list-item":
                index = existing_value[0]
                existing_list = existing_value[1]
                existing_value = existing_list[index] if len(existing_list) > index else None
            
            last_in_object = len(stack) > 0 and stack[0] != "DEDENT"
            line_end = "," if last_in_object else ""

            if k != "":
                "{indent}\"{k}\":"
            
            if key_type is str:
                if type(existing_value) is str:
                    "\"{existing_value}\"{line_end}"
                else:
                    '"[STRING_VALUE]"{line_end}' where STOPS_BEFORE(STRING_VALUE, '"') and \
                        STOPS_AT(COMMA_OR_BRACKET, ",") and ESCAPED(STRING_VALUE) and STOPS_BEFORE(STRING_VALUE, '"')
            elif key_type is int:
                if type(existing_value) is int:
                    "{existing_value}{line_end}"
                else:
                    # Chat API models do not support advanced integer constraints
                    if "turbo" in context.interpreter.model_identifier or "gpt-4" in context.interpreter.model_identifier:
                        "[INT_VALUE]" where STOPS_AT(INT_VALUE, ",") and len(TOKENS(INT_VALUE)) < 4
                        if line_end.startswith(",") and not INT_VALUE.endswith(","):
                            ","
                    else:
                        "[INT_VALUE]" where INT(INT_VALUE) and len(TOKENS(INT_VALUE)) < 4
                        if line_end.startswith(","):
                            ","
            elif type(key_type) is dict:
                "{{"
                if type(existing_value) is not dict:
                    existing_value = None
                existing_value = existing_value or {}
                indent += ""
                stack = [(k, "dict-item", key_type[k], existing_value.get(k)) for k in key_type.keys()] + ["DEDENT", f"}}{line_end}"] + stack
            elif type(key_type) is list:
                "["
                existing_value = existing_value or []
                indent += ""
                stack = [("", "list-item", key_type[0], (0, existing_value))] + ["DEDENT", f"]{line_end}"] + stack
            else:
                assert False, "not a supported type " + str(k) + " " + str(key_type)
            
            multiplicity = "n" if element_type == "list-item" and len(stack) > 1 and stack[0] == "DEDENT" and stack[1].startswith("]") else "1"

            if multiplicity == "n":
                # check if another list-item should follow
                "[COMMA_OR_BRACKET]" where STOPS_AT(COMMA_OR_BRACKET, ",") and STOPS_AT(COMMA_OR_BRACKET, "]") and ERASE(COMMA_OR_BRACKET)
                if not "]" in COMMA_OR_BRACKET:
                    ","
                    stack = [("", "list-item", key_type, (index+1, existing_list))] + stack
                else:
                    pass
        elif t == "DEDENT":
            indent = indent[:-1]
        elif type(t) is str:
            "{indent}{t}"
        else:
            assert False, "not a supported type" + str(t)
    payload = context.prompt.rsplit("JSON: ",1)[1]
    try:
        json_payload = json.loads(payload)
    except Exception as e:
        print("Failed to parse JSON from", payload)
    return type_dict_to_type_instance(json_payload, ty)
    '''