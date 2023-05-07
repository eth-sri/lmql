import lmql
import json

@lmql.query
async def single_shot_as_type(s, ty):
    '''lmql
    argmax(openai_chunksize=1024)
        schema_description = lmql.types.schema_description(ty)
        "Provided a data schema of the following schema: {schema_description}\n"
        "Translate the following into a JSON payload: {s}\n"
        "JSON: [JSON]"
        return JSON
    from 
        "chatgpt"
    '''

@lmql.query
async def is_type(ty):
    '''lmql
    incontext
        # first run a simple one-shot query to get an initial result
        simple_json_result = single_shot_as_type(context.prompt, ty)
        try:
            already_parsed = json.loads(simple_json_result)
        except:
            already_parsed = {}
        
        # then do scripted parsing as a fallback (does not query the model if already_parsed already contains all the keys we need)
        "As JSON: "
        schema = lmql.types.schema(ty)
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
                        '"[STRING_VALUE]"{line_end}'
                elif key_type is int:
                    if type(existing_value) is int:
                        "{existing_value}{line_end}"
                    else:
                        "[INT_VALUE]"
                        if not (INT_VALUE.endswith(",") and line_end.startswith(",")):
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
                    "[COMMA_OR_BRACKET]"
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
        json_payload = json.loads(payload)
        return lmql.types.dict_to_type_instance(json_payload, ty)
    where
        STOPS_BEFORE(STRING_VALUE, '"') and STOPS_AT(INT_VALUE, ",") and ESCAPED(STRING_VALUE) and STOPS_AT(COMMA_OR_BRACKET, "]") and STOPS_AT(COMMA_OR_BRACKET, ",") and ERASE(COMMA_OR_BRACKET)
    '''