"""
Dispatching implementation for a simple HTTP fetch() function.

Dispatches to the LMQL Browser Runtime if the LMQL_BROWSER environment variable is set, 
otherwise uses aiohttp.

For browser use this is required, as the native Python networking stack
is not available when running via Pyodide.
"""

import os
import json
    
if "LMQL_BROWSER" in os.environ:
    import js
    from pyodide.ffi import to_js
    
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
else:
    import aiohttp
    
    async def fetch(url, path=None):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if path is not None:
                    result = await response.json()
                    path = path.split(".")
                    for p in path:
                        if type(result) is list:
                            p = int(p)
                        result = result[p]
                    return result
                else:
                    return await response.text()