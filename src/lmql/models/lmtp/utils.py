import torch

def rename_model_args(model_args):
    cuda = model_args.pop("cuda", False)
    dtype = model_args.pop("dtype", None)

    # parse dtype
    if dtype is not None:
        model_args["torch_dtype"] = dtype
    
    if dtype == "float16":
        model_args["torch_dtype"] = torch.float16
    elif dtype == "8bit":
        model_args["load_in_8bit"] = dtype == "8bit"

    # parse cuda
    if cuda:
        model_args["device_map"] = "auto"
    
    return model_args