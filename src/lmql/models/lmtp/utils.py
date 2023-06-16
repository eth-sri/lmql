import torch


def rename_model_args(model_args):
    cuda = model_args.pop("cuda", False)
    dtype = model_args.pop("dtype", None)

    if dtype == "4bit":
        model_args["load_in_4bit"] = True
    elif dtype == "8bit":
        model_args["load_in_8bit"] = True
    elif dtype is not None:
        model_args["torch_dtype"] = getattr(torch, dtype)

    # parse cuda
    if cuda:
        model_args["device_map"] = "auto"

    return model_args
