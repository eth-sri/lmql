from .queries import query_from_string

async def run_file(filepath, *args, output_writer=None, force_model=None, **kwargs):
    import inspect
    with open(filepath, "r") as f:
        code = f.read()
    
    q = query_from_string(code, output_writer=output_writer)
    return await q(*args, **kwargs)

async def run(code, *args, **kwargs):
    """
    Compiles and runs the given query string asynchronously.

    For synchronous execution (w/o await), use `lmql.run_sync` instead.
    """
    q = query_from_string(code, output_writer=kwargs.get("output_writer", None))
    return await q(*args, **kwargs)
        
def run_sync(code, *args, **kwargs):
    """
    Compiles and runs the given query string synchronously.

    For async execution, use `lmql.run` instead.
    """
    q = query_from_string(code, is_async=False)
    return q(*args, **kwargs)
