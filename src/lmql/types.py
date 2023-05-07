from dataclasses import dataclass, fields, is_dataclass
from typing import List

def schema(t):
    if is_dataclass(t):
        return {f.name: schema(f.type) for f in fields(t)}
    elif t is int:
        return int
    elif t is str:
        return str
    elif hasattr(t, "__origin__") and t.__origin__ is list:
        element_type = t.__args__[0]
        return [schema(element_type)]
    else:
        assert False, "not a supported type " + str(t)

def schema_description(t):
    s = schema(t)
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

def dict_to_type_instance(data, t):
    if is_dataclass(t):
        return t(**{f.name: dict_to_type_instance(data[f.name], f.type) for f in fields(t)})
    elif t is int:
        return int(data)
    elif t is str:
        return str(data)
    elif hasattr(t, "__origin__") and t.__origin__ is list:
        element_type = t.__args__[0]
        return [dict_to_type_instance(d, element_type) for d in data]
    else:
        assert False, "not a supported type " + str(t)