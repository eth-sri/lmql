import ast

def _dedent(source):
    # remove common indent
    common_indent = None
    lines = []
    for line in source.splitlines():
        if line.strip() == "" or line.strip() == '"""lmql' or line.strip() == "'''lmql":
            lines.append(line)
            continue
        if common_indent is None:
            common_indent = len(line) - len(line.lstrip())
        else:
            common_indent = min(common_indent, len(line) - len(line.lstrip()))
        lines.append(line[common_indent:])
    return "\n".join(lines)

def get_decorated_function_code(fct):
    import ast
    import inspect

    source = ""

    try:
        source = inspect.getsource(fct)
        # dedent source
        source = _dedent(source)

        tree = ast.parse(source)
        docstring_element = tree.body[0].body[0].value
        # get range of source that corresonds to the docstring
        start = docstring_element.lineno
        end = docstring_element.end_lineno
        startcol = docstring_element.col_offset
        endcol = docstring_element.end_col_offset
        
        # get source code of the function
        source = source.splitlines()

        # remove common indent
        common_indent = None
        lines = []
        for line in source[start-1:end]:
            if line.strip() == "" or line.strip() == '"""lmql' or line.strip() == "'''lmql":
                lines.append(line)
                continue
            if common_indent is None:
                common_indent = len(line) - len(line.lstrip())
            else:
                common_indent = min(common_indent, len(line) - len(line.lstrip()))
            lines.append(line[common_indent:])
        lines[0] = lines[0][startcol - common_indent:]
        lines[-1] = lines[-1][:endcol]

        source = "\n".join(lines)

        quote_types = "'''" if source.endswith("'''") else '"""'
        if source.lstrip().startswith(quote_types):
            source = source.lstrip()[len(quote_types):]
        assert source.endswith(quote_types), f"Docstring of @lmql.query function {fct.__name__} must be on the first line of the function, but is:\n {source}"
        source = source[:-len(quote_types)].strip("\n")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise RuntimeError("Failed to parse docstring of query function as LMQL code:\n\n" + str(source))

    return source
