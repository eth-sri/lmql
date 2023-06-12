from docutils import nodes
from docutils.parsers.rst import Directive
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.token import Name, Keyword
from pygments.formatters import HtmlFormatter

import os
import json

class LmqlLexer(PythonLexer):
    EXTRA_KEYWORDS = set((
        "BEAM",
        "beam",
        "ARGMAX",
        "argmax",
        "SAMPLE",
        "BEST_K",
        "best_k",
        "BEAM_VAR",
        "beam_var",
        "VAR",
        "var",
        "sample",
        "FROM",
        "from",
        "WHERE",
        "where",
        "DISTRIBUTION",
        "distribution",
        "class"
    ))

    def get_tokens_unprocessed(self, text):
        for index, token, value in PythonLexer.get_tokens_unprocessed(self, text):
            if token is Name and value in self.EXTRA_KEYWORDS:
                yield index, Keyword.Pseudo, value
            else:
                yield index, token, value
        
def output_format(output):
    print([output])

    variable_name = None
    result = ""
    is_escape = False
    offset = -1

    var_ids = {}
    var_ctr = 1

    while offset < len(output) - 1:
        offset += 1

        c = output[offset]

        if is_escape and (c == "[" or c == "]"):
            result += c
            is_escape = False
            offset += 1
            continue
        is_escape = False

        if c == "\\":
            is_escape = True
            continue

        if c == "[" and variable_name is None:
            start_offset = offset + 1
            print("parsing variable name", output[start_offset:], flush=True)
            while output[offset] != " " and output[offset] != "]":
                offset += 1
            variable_name = output[start_offset:offset]
            if variable_name not in var_ids:
                var_ids[variable_name] = var_ctr
                var_ctr += 1
            var_id = var_ids[variable_name]

            result += "<span class=\"variable val" + str(var_id) + "\"><span class=\"variable-name\">" + variable_name + "</span>"
            offset -= 1
            continue
        
        if c == "]" and variable_name is not None:
            result += "</span>"
            variable_name = None
            continue
        result += c
    
    return result

class LmqlSnippet(Directive):
    has_content = True

    def run(self):
        code = []
        output = []
        is_output = False
        name = None
        noplayground = False

        for l in self.content:
            if l.startswith("name::"):
                name = l[6:]
            elif l.startswith("noplayground::"):
                noplayground = True
            elif l.startswith("model-output::"):
                is_output = True
            else:
                if is_output: output += [l]
                else: code += [l]
        
        code = "\n".join(code)
        original_code = code
        
        assert name is not None, "name:: is required for lmql directive in {}".format(self.state.document.current_source)

        # compute snippet_id
        outdir = self.state.document.settings.env.app.outdir
        # make sure doc-snippets exists
        if not os.path.exists(os.path.join(outdir, "doc-snippets")):
            os.makedirs(os.path.join(outdir, "doc-snippets"))
        snippet_id = os.path.relpath(self.state.document.current_source, self.state.document.settings.env.srcdir)
        # replace all but A-z0-9 with -
        snippet_id = "".join([c if c.isalnum() else "-" for c in snippet_id])
        snippet_id += "-" + name

        # create output
        paragraph_node = nodes.paragraph()
        if not noplayground:
            prefix = """<button href onclick="openPlaygroundSnippet(this, 'doc-snippets/{}')">Open In Playground</button>""".format(snippet_id)
        else:
            prefix = ""

        code = highlight(code, LmqlLexer(), HtmlFormatter(cssclass="highlight lmql"))
        code = code.replace("""<div class="highlight lmql">""", """<div class="highlight lmql">""" + prefix)
        
        # model output highlight
        if len(output) > 0:
            print(output_format(output), flush=True)
            output = "\n".join(output)
            output_template = "<div class=\"highlight-model-output notranslate\"><div class=\"highlight\">{}</div></div>".format(output_format(output))
            code += output_template
        
        paragraph_node += nodes.raw('', code, format='html')
        
        # save snippet separately
        snippet_path = os.path.join(outdir, "doc-snippets", snippet_id + ".json")

        with open(snippet_path, "w") as f:
            playground_data = {
                "lmql-editor-contents": original_code.strip(),
                "decoder-graph": json.dumps({
                    "nodes": [],
                    "edges": []
                })
            }
            f.write(json.dumps(playground_data))

        return [paragraph_node]

def setup(app):
    app.add_directive("lmql", LmqlSnippet)
    app.add_css_file('css/lmql-docs.css')
    app.add_js_file('js/lmql-playground.js')

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    } 

if __name__ == "__main__":
    s = """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.⏎', 'Q: What is the underlying sentiment of this review and why?⏎', 'A: [ANALYSIS The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]⏎', 'Based on this, the overall sentiment of the message can be considered to be [CLASSIFICATION]"""
    print(output_format(s))