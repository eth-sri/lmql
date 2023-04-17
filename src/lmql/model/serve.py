"""
Serves a model as LMQL inference API.
"""

from http.server import HTTPServer

import multiprocessing

import argparse


from lmql.model import serve_hf, serve_llama_cpp
from lmql.model.serve_types import InferenceServerState, LMQLInferenceAPIHandler
import lmql.model.serve_hf
import lmql.model.serve_llama_cpp

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "model",
        type=str,
        help="the huggingface model to use if not llama.cpp else the huggingface tokenizer to proxy the llama.cpp one.",
    )
    parser.add_argument(
        "--llama.cpp",
        action="store_true",
        dest="llama_cpp",
        help="flag determining whether to use llama.cpp server or not.",
    )
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--cuda", action="store_true", default=False)
    parser.add_argument("--cache", type=str, default=None)
    parser.add_argument(
        "--num-tokenizer-processes", type=int, default=2, dest="num_tokenizer_processes"
    )
    parser.add_argument("--tokenizer", type=str, default=None)
    parser.add_argument("--dtype", type=str, default="none")

    serve_hf.add_parser(parser)
    serve_llama_cpp.add_parser(parser)

    args = parser.parse_args()

    manager = multiprocessing.Manager()

    # prepare configuration
    model_descriptor = args.model
    tokenizer_descriptor = args.tokenizer
    if tokenizer_descriptor is None:
        tokenizer_descriptor = model_descriptor

    state = InferenceServerState(
        model_descriptor,
        tokenizer_descriptor,
        args.dtype,
        queue=manager.Queue(),
        tokenize_queue=manager.Queue(),
        all_results_queue=manager.Queue(),
    )

    if args.llama_cpp:
        processor, tokenizer_processor = serve_llama_cpp.get_serve(state, args)
    else:
        processor, tokenizer_processor = serve_hf.get_serve(state, args)
    # run inference API server in this process
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, LMQLInferenceAPIHandler)
    httpd.state = state

    try:
        print("Serving LMQL inference API on {}:{}".format(args.host, args.port))
        httpd.serve_forever()
    except KeyboardInterrupt:
        # terminate server
        httpd.shutdown()
        httpd.server_close()
        print("Server stopped")

    # terminate processors
    processor.shutdown()
    tokenizer_processor.shutdown()
