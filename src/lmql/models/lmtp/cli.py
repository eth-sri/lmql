from .lmtp_server import *

global args
args = None

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

def lmtp_serve_main(model_args):
    """
    CLI for starting an LMTP server with a given HuggingFace 'transformers' model.
    """

    # extract explicit arguments
    host = args.pop("host", "localhost")
    port = args.pop("port", 8080)
    model = args.pop("model", None)
    static = args.pop("static", False)
    
    # check 'auto' vs static
    assert not static or model != "auto", "Cannot use --static mode with model 'auto'. Please specify a specific model."

    # all other arguments are model arguments
    model_args = rename_model_args(args)    

    # stream endpoint
    async def stream(request):
        # bidirectional websocket 
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await LMTPWebSocketTransport.listen(ws, model_args)

    if model != "auto":
        Scheduler.instance(model, model_args, user=None)

    app = web.Application()
    app.add_routes([web.get('/', stream)])
    web.run_app(app, host=host, port=port)

def argparser(args):
    next_argument_name = None
    
    kwargs = {}
    flag_args = ["cuda", "static"]

    help_text = """
usage: serve-model [-h] [--port PORT] [--host HOST] [--cuda] [--dtype DTYPE] [--[*] VALUE] model

positional arguments:
  model          The model to load or 'auto' if the model should be automatically loaded on client request.

options:
  -h, --help     show this help message and exit
  --port PORT
  --host HOST
  --cuda
  --static      If set, the model cannot be switched on client request but remains fixed to the model specified in the model argument.
  --dtype DTYPE  What format to load the model weights. Options: 'float16'
                 (not available on all models), '8bit' (requires bitsandbytes)
  --[*] VALUE   Any other argument will be passed as a keyword argument to the AutoModelForCausalLM.from_pretrained function.
    """

    for arg in args:
        if arg == "-h" or arg == "--help":
            print(help_text)
            sys.exit(0)
        if arg.startswith("--"):
            assert next_argument_name is None
            next_argument_name = arg[2:]
            if next_argument_name in flag_args:
                kwargs[next_argument_name] = True
                next_argument_name = None
        else:
            if next_argument_name is None:
                assert not "model" in kwargs, "Positional argument 'model' already specified"
                kwargs["model"] = arg
            else:
                assert next_argument_name is not None
                if arg == "True": arg = True
                elif arg == "False": arg = False

                kwargs[next_argument_name] = arg
                next_argument_name = None

    if not "model" in kwargs:
        kwargs["model"] = "auto"

    assert next_argument_name is None, "Missing value for argument {}".format(next_argument_name)

    if len(kwargs) == 0:
        print(help_text)
        sys.exit(0)

    return kwargs

if __name__ == "__main__":
    args = argparser(sys.argv[1:])
    lmtp_serve_main(args)