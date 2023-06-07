from .lmtp_inference_server import *
from .utils import rename_model_args

def serve(model_name, host="localhost", port=8080, cuda=False, dtype=None, static=False, **kwargs):
    """
    Serves the provided model as an LMTP/LMQL inference endpoint.

    Args:
        model_name (str): The model to load or 'auto' if any model should automatically be loaded on client request.
        host (str, optional): The host to serve the model on. Defaults to "localhost".
        port (int, optional): The port to serve the model on. Defaults to 8080.
        cuda (bool, optional): If set, the model will be loaded on the GPU. Defaults to False.
        dtype (str, optional): What format to load the model weights. Options: 'float16' (not available on all models), '8bit' (requires bitsandbytes). Defaults to None.
        static (bool, optional): If set, the model cannot be switched on client request but remains fixed to the model specified in the model argument. Defaults to False.
        **kwargs: Any other argument will be passed as a keyword argument to the AutoModelForCausalLM.from_pretrained function.

    """
    return lmtp_serve_main({
        "model": model_name,
        "host": host,
        "port": port,
        "cuda": cuda,
        "dtype": dtype,
        "static": static,
        **kwargs
    })

def lmtp_serve_main(model_args):
    """
    CLI for starting an LMTP server with a given HuggingFace 'transformers' model.
    """

    # extract explicit arguments
    host = model_args.pop("host", "localhost")
    port = model_args.pop("port", 8080)
    model = model_args.pop("model", None)
    static = model_args.pop("static", False)
    
    # check 'auto' vs static
    assert not static or model != "auto", "Cannot use --static mode with model 'auto'. Please specify a specific model."

    # all other arguments are model arguments
    model_args = rename_model_args(model_args)    

    # stream endpoint
    async def stream(request):
        # bidirectional websocket 
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await LMTPWebSocketTransport.listen(ws, model_args, static=static)

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