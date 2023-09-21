from lmql.models.lmtp.utils import rename_model_args

import warnings
lmtp_model_inprocess_instances = {}

def inprocess(model_name, use_existing_configuration=False, **kwargs):
    """
    Loads a 'transformers' model in-process and returns an LMQLModelDescriptor object
    to use this in-process model in LMQL.

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
    from .lmtp_dcmodel import lmtp_model
    assert not model_name.startswith("openai/"), "openai/ models cannot be loaded with inprocess=True, they always use the remote API."

    # extract/reassign renamed like 'cuda'
    kwargs = rename_model_args(kwargs)

    # special case for 'llama.cpp'
    if model_name.startswith("llama.cpp:"):
        # kwargs["async_transport"] = True
        if "tokenizer" not in kwargs:
            warnings.warn("By default LMQL uses the '{}' tokenizer for all llama.cpp models. To change this, set the 'tokenizer' argument of your lmql.model(...) object.".format("huggyllama/llama-7b", UserWarning))
        kwargs["tokenizer"] = kwargs.get("tokenizer", "huggyllama/llama-7b")

    if "endpoint" in kwargs:
        warnings.warn("info: 'endpoint' argument is ignored for inprocess=True/local: models.")

    cmdline_args = f"{model_name} "
    for k,v in kwargs.items():
        if type(v) is bool:
            cmdline_args += f"--{k} "
        else:
            cmdline_args += f"--{k} {v} "

    global lmtp_model_inprocess_instances

    if cmdline_args in lmtp_model_inprocess_instances.keys():
        return lmtp_model_inprocess_instances[cmdline_args]

    kwargs["inprocess"] = True
    model = lmtp_model(model_name, **kwargs)
    lmtp_model_inprocess_instances[cmdline_args] = model
    return model