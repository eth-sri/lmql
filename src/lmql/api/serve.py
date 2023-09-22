def serve(*args, **kwargs):
    """
    See lmql.models.lmtp.lmtp_serve.serve.
    """
    import os
    assert not "LMQL_BROWSER" in os.environ, "lmql.serve is not available in the browser distribution of LMQL."
    from lmql.models.lmtp.lmtp_serve import serve
    return serve(*args, **kwargs)