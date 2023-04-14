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
    
    for category in queries:
        print(f"{category['category']}")
        for query in category["queries"]:
            # rpad
            rpad = 50 - len(query["name"])
            if rpad < 0:
                rpad = 0

            print(f" - {query['name']}{' ' * rpad}", end=" ")
            # run query
            try:
                s = time.time()
                error_buffer = io.StringIO()
                sys.stderr = error_buffer
                await lmql.run(query["code"], output_writer=lmql.headless)
                print(termcolor.colored("[OK]", "green"), f"({time.time() - s:.2f}s)")
            except Exception as e:
                print(error_buffer.getvalue())
                print(termcolor.colored("[FAIL]", "red"), f"({time.time() - s:.2f}s)")


if __name__ == "__main__":
    asyncio.run(main())