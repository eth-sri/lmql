from .lmtp_dcmodel import lmtp_model

global inprocess_models
inprocess_models = {}

def inprocess(model_name, use_existing_configuration=False, **kwargs):
    """
    Loads a 'transformers' model in-process.

    This is useful when you don't want to spawn a separate 'lmql serve-model' process.

    The returned in-process models are cached so that subsequent calls with the same arguments will return the same object.

    Args:
        model_name (str): Name of the model to load, as it occurs in the HuggingFace Transformers registry. (e.g. gpt2)
        
        use_existing_configuration (bool): If True, will return an existing in-process model with the same model name, but possibly different arguments.
        
        kwargs: Additional arguments to pass to the serve-model command line. (see lmql serve-model --help)
                For this, use keys as they occur in the command line, e.g. 'port' for '--port' and for
                boolean flags, use True/False as values, e.g. 'cuda=True' for '--cuda'.
    Return:
        InProcessServer: An object representing the loaded model, can be passed in the 'from' clause of a query.
    """
    cmdline_args = f"{model_name} "
    for k,v in kwargs.items():
        if type(v) is bool:
            cmdline_args += f"--{k} "
        else:
            cmdline_args += f"--{k} {v} "
    cmdline_args += "--subprocess"

    if cmdline_args in inprocess_models:
        return inprocess_models[cmdline_args]
    
    if use_existing_configuration:
        # find existing match for model_name only
        for cmdargs, p in inprocess_models.items():
            if cmdargs.split(" ")[0] == model_name:
                return p
    
    model = lmtp_model(model_name, inprocess=True)
    inprocess_models[cmdline_args] = model
    return model