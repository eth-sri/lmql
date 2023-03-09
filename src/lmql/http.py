import os
import json

if "LMQL_BROWSER" in os.environ:
    import js
    from pyodide.ffi import to_js
else:
    assert False, "No lmql.http implementation available"

async def fetch(url, path=None):
    error, result = await js.fetch_bridge(url, {
        "method": "GET",
        "mode": "no-cors"
    })

    if error: raise Exception(error)

    if path is not None:
        result = json.loads(result)
        path = path.split(".")
        for p in path:
            if type(result) is list:
                p = int(p)
            print(p, result)
            result = result[p]
        return result
    else:
        return result
