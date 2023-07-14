import asyncio
import json
import lmql
import subprocess
import os
import tempfile
import sys
import time
import io
import termcolor

from lmql.runtime.tokenizer import load_tokenizer
from lmql.runtime.stats import Stats

# load queries by executing ../ui/playground/src/queries.js via node and getting the object of module.exports

def load_queries():
    # file dir
    cwd = os.path.dirname(os.path.realpath(__file__))
    # js file to require file and console.log .queries
    contents = f"""
    require = require("{os.path.join(cwd, "..", "ui", "playground", "src", "queries.js")}")
    console.log(JSON.stringify(require.queries))
    """
    # write contents to temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(contents)
        f.flush()
        # run node on temp file
        queries = subprocess.check_output(["node", f.name]).decode("utf-8")
        # delete temp file
        os.remove(f.name)
    # return queries
    return json.loads(queries)


async def main():
    print("Loading example queries from ../ui/playground/src/queries.js...")
    queries = load_queries()
    stderr = sys.stderr

    print("\nTokenizer Backend: ", type(load_tokenizer("text-davinci-003").tokenizer_impl).__name__, "\n")
    
    api_stats = Stats("openai-api")

    for category in queries:
        print(f"{category['category']}")
        
        if "requires_input" in category.keys() and category["requires_input"]:
            print(" [Skipping because it requires user input]".format(category["category"]))
            continue
        
        for query in category["queries"]:
            # rpad
            rpad = 50 - len(query["name"])
            if rpad < 0:
                rpad = 0

            print(f" - {query['name']}{'.' * rpad}", end=" ", flush=True)

            api_stats.times["first-chunk-latency"] = 0
            
            # run query
            try:
                s = time.time()
                error_buffer = io.StringIO()
                sys.stderr = error_buffer
                await lmql.run(query["code"], output_writer=lmql.headless)
                runtime = time.time() - s
                # time minus api latency
                latency = api_stats.times.get("first-chunk-latency", 0)
                print(termcolor.colored("[OK]", "green"), f"({runtime:.2f}s, w/o latency: {(runtime - latency):.2f}s)")
            except Exception as e:
                print(error_buffer.getvalue())
                print(e)
                print(termcolor.colored("[FAIL]", "red"), f"({time.time() - s:.2f}s)")


if __name__ == "__main__":
    asyncio.run(main())