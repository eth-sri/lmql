"""
Utilities for running LMQL queries (a)synchronously.

By default LMQL is asynchronous, meaning that you have to use `await` when calling LMQL queries.

Nonetheless, we provide a synchronous interface for LMQL queries, which internally relies
on `call_sync` to run the query in an internal `lmql_loop` event loop.

However, to avoid deadlocks and nested event loops, we do not allow call `call_sync` from within
an existing async context. Instead, we recommend users switch to the async interface and use `await` 
in this case.
"""

from typing import List, Dict, Any

global lmql_loop
lmql_loop = None

def call_sync(lmql_query_function, *args, **kwargs):
    import asyncio
    global lmql_loop

    if lmql_loop is None:
        try:
            lmql_loop = asyncio.get_event_loop()
        except RuntimeError as e:
            lmql_loop = asyncio.new_event_loop()
    loop = lmql_loop
    
    asyncio.set_event_loop(loop)

    task = lmql_query_function.__acall__(*args, **kwargs)
    error = None
    
    try:
        res = loop.run_until_complete(task)
    except RuntimeError as e:
        if "This event loop is already running" in str(e) or "Cannot run the event loop while another loop is running" in str(e):
            error = AssertionError("LMQL queries cannot be called synchronously from within an async context. Please use async queries and await them instead.")
        else:
            error = e
        asyncio.ensure_future(task).cancel()
        
    if error is not None:
        raise error

    return res

def main(query_fct, *args, **kwargs):
    """
    Runs the provided query function in the main thread
    and returns the result.

    This call is blocking.
    """
    import asyncio
    
    global lmql_loop
    if lmql_loop is None:
        lmql_loop = asyncio.new_event_loop()

    loop = lmql_loop
    asyncio.set_event_loop(loop)

    return loop.run_until_complete(query_fct(*args, **kwargs))
