"""
Command Line Interface for lmtp_inference_server.py.
"""

from .lmtp_inference_server import *
from .utils import rename_model_args

def serve(model_name, host="localhost", port=8080, cuda=False, dtype=None, static=False, loader=None, **kwargs):
    """
    Serves the provided model as an LMTP/LMQL inference endpoint.

    Args:
        model_name (str): The model to load or 'auto' if any model should automatically be loaded on client request.
        host (str, optional): The host to serve the model on. Defaults to "localhost".
        port (int, optional): The port to serve the model on. Defaults to 8080.
        single_thread (bool, optional): If set, the model and the inference server will run in the same thread. Defaults to False. This can lead to increased latency when processing multiple requests, but may be required depending on model implementation.
        cuda (bool, optional): If set, the model will be loaded on the GPU. Defaults to False.
        dtype (str, optional): What format to load the model weights. Options: 'float16' (not available on all models), '8bit' (requires bitsandbytes). Defaults to None.
        static (bool, optional): If set, the model cannot be switched on client request but remains fixed to the model specified in the model argument. Defaults to False.
        loader (str, optional): If set, the model will be loaded using a library other than transformers. This is useful when loading quantized models in formats that are not yet supported by Transformers (like GTPQ). Defaults to None.
        **kwargs: Any other argument will be passed as a keyword argument to the AutoModelForCausalLM.from_pretrained function.

    """
    return lmtp_serve_main({
        "model": model_name,
        "host": host,
        "port": port,
        "cuda": cuda,
        "dtype": dtype,
        "static": static,
        "loader": loader,
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
    single_thread = model_args.pop("single_thread", False)
    static = model_args.pop("static", False) or single_thread
    
    assert not single_thread or model != "auto", "Cannot use --single_thread mode with model 'auto'. Please specify a specific model to load."

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

    if model != "auto" and not single_thread:
        Scheduler.instance(model, model_args, user=None)

    app = web.Application()
    app.add_routes([web.get('/', stream)])
    
    def web_print(*args):
        if len(args) == 1 and args[0].startswith("======== Running on"):
            print(f"[Serving LMTP endpoint on ws://{host}:{port}/]")
        else:
            print(*args)
    
    # r executor
    tasks = [web._run_app(app, host=host, port=port, print=web_print)]
    if static and single_thread:
        tasks += [Scheduler.instance(model, model_args, user=None, sync=True).async_worker()]
    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

def argparser(args):
    next_argument_name = None
    
    kwargs = {}
    flag_args = ["cuda", "static", "single_thread"]

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
  --loader OPT  If set, the model will be loaded using the corresponding option. Useful for loading quantized modules in formats not
                supported by the transformers library, like GPTQ. Available options:
                * auto-gptq (loads GPTQ based quantized models with auto-gptq. Consider adding `--use_safetensors true` if the model is
                             distributed in the safetensor format)
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
                else:
                    try:
                        arg = int(arg)
                    except:
                        try:
                            arg = float(arg)
                        except:
                            arg = str(arg)


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