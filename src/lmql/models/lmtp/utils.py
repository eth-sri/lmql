from transformers import BitsAndBytesConfig
import warnings


def rename_model_args(model_args):
    cuda = model_args.pop("cuda", False)
    bits = model_args.pop("bits", 16)
    dtype = model_args.pop("dtype", None)
    q_config = model_args.pop("quantization_config", None)

    if bits == 4:
        model_args["load_in_4bit"] = True
    elif bits == 8:
        model_args["load_in_8bit"] = True

    if dtype is not None:
        import torch
        model_args["torch_dtype"] = getattr(torch, dtype)

    if type(q_config) is set:
        q_config = {k: v for k, v in q_config.pop()}
        model_args["quantization_config"] = BitsAndBytesConfig(**q_config)
    elif q_config is not None:
        warnings.warn(
            "quantization_config is not a frozenset, so it will not be used. Use frozenset(Create BitsAndBytesConfig.__dict__.items()) instead.")

    # parse cuda
    if cuda:
        if "device_map" in model_args:
            print("Warning: device_map is set, but cuda is True. Ignoring 'cuda' which would set device_map to 'auto'.")
        else:
            model_args["device_map"] = "auto"

    return model_args
