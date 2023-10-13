"""
Formatting of values in a prompt context.
"""

def unescape(s):
    return str(s).replace("[", "[[").replace("]", "]]")

def is_chat_list(l):
    if not isinstance(l, list):
        return False
    if any(not isinstance(x, dict) for x in l):
        return False
    
    # keys can be role and content
    if any(x not in ["role", "content"] for x in l[0].keys()):
        return False
    
    return True

def format_chat(chat):
    qstring = ""
    
    for m in chat:
        qstring += f"<lmql:{m['role']}/>{m['content']}"
    
    return qstring

def tag(t):
    return f"<lmql:{t}/>"

def format(s):
    """
    Formats a value for insertion into an LMQL query string, i.e. the LLM prompt.
    """
    if is_chat_list(s):
        return format_chat(s)

    return unescape(s)