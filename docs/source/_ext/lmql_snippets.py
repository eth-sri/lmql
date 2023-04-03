from docutils import nodes
from docutils.parsers.rst import Directive
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.token import Name, Keyword
from pygments.formatters import HtmlFormatter

import os
import json

PLAYGROUND_URL = "https://lbeurerkellner.github.io/green-gold-dachshund-web/playground"
# PLAYGROUND_URL = "http://localhost:3000"

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
        "distribution")
    )

    def get_tokens_unprocessed(self, text):
        for index, token, value in PythonLexer.get_tokens_unprocessed(self, text):
            if token is Name and value in self.EXTRA_KEYWORDS:
                yield index, Keyword.Pseudo, value
            else:
                yield index, token, value
        

class LmqlSnippet(Directive):
    has_content = True

    def run(self):
        code = []
        name = None

        for l in self.content:
            if l.startswith("name::"):
                name = l[6:]
            else:
                code += [l]
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
        prefix = """<button href onclick="openPlaygroundSnippet(this, 'doc-snippets/{}', '{}')">Open In Playground</button>""".format(snippet_id, PLAYGROUND_URL)

        code = highlight(code, LmqlLexer(), HtmlFormatter(cssclass="highlight lmql"))
        code = code.replace("""<div class="highlight lmql">""", """<div class="highlight lmql">""" + prefix)
        paragraph_node += nodes.raw('', code, format='html')
        
        # save snippet separately
        snippet_path = os.path.join(outdir, "doc-snippets", snippet_id + ".json")

        with open(snippet_path, "w") as f:
            playground_data = {
                "lmql-editor-contents": original_code
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