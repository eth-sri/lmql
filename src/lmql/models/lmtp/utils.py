def rename_model_args(model_args):
    cuda = model_args.pop("cuda", False)
    dtype = model_args.pop("dtype", None)

    if dtype == "4bit":
        model_args["load_in_4bit"] = True
    elif dtype == "8bit":
        model_args["load_in_8bit"] = True
    elif dtype is not None:
        import torch
        model_args["torch_dtype"] = getattr(torch, dtype)

    # parse cuda
    if cuda:
        if "device_map" in model_args:
            print("Warning: device_map is set, but cuda is True. Ignoring 'cuda' which would set device_map to 'auto'.")
        else:
            model_args["device_map"] = "auto"

    return model_args
