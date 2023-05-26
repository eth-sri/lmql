import re

def to_int(s: str):
    if type(s) is not str:
        return s
    # remove all but numeric
    s = re.sub(r"[^0-9\.\-]", "", s)
    is_negative = s.startswith("-")
    s = s.replace("-", "")
    if len(s) == 0:
        return None
    if len(s.replace(".", "")) == 0:
        return None
    if s.count(".") > 1:
        return None

    return int(float(s)) * (-1 if is_negative else 1)

def eq_int(a, b):
    if type(a) is str:
        a = to_int(a)
    if type(b) is str:
        b = to_int(b)
    return a == b

def is_eq_int(a, b):
    if type(a) is str:
        a = a.strip()
    if type(b) is str:
        b = b.strip()
    if not eq_int(a, b):
        print("assertion failure: " + f"Equality {a} == {b} does not hold, after conversion we get {to_int(a)} != {to_int(b)}")
        return f"{a} != {b} X"
    return f"{a} = {b} ✓"

def check_is_eq_int(a, b):
    result = is_eq_int(a, b)
    return result.endswith("✓")