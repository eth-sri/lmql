import re
from dataclasses import dataclass

@dataclass
class TemplateVariable:
    name: str

@dataclass
class DistributionVariable:
    name: str

def qstring_to_stmts(qstring):
    stmts = []
    offset = 0
    for match in re.finditer("\[[A-Za-z0-9:_]+\]", qstring):
        new_offset = match.span()[0]

        # append string preceding template var
        previous_string = qstring[offset:new_offset]
        if len(previous_string) != 0: stmts.append(previous_string)

        name = qstring[match.span()[0]: match.span()[1]][1:-1]
        if name.startswith("distribution:"):
            stmts.append(DistributionVariable(name[len("distribution:"):]))
        else:
            # append template var
            stmts.append(TemplateVariable(name))
        
        # advance pointer
        offset = match.span()[1]
    
    # append string suffix
    previous_string = qstring[offset:]
    if len(previous_string) != 0: stmts.append(previous_string)

    return stmts