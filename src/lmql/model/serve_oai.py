import sys
import asyncio
import aiohttp
import signal
import subprocess
import os
import argparse
import psutil
import concurrent
from aiohttp import web
from aiohttp_sse import sse_response
from queue import Queue
from threading import Event
from typing import Optional, Tuple

from typing import List
from dataclasses import dataclass
from transformers import StoppingCriteria, AutoModelForCausalLM, AutoTokenizer
import tokenize
import json
import torch
import termcolor
import time

def make_float(v): 
    return float(f"{v:.5f}")

class Logger(StoppingCriteria):
    """
    A streaming token logger disguised as a stopping criteria.

    Also acts as a stopping criteria.
    """
    def __init__(self, stopping_phrases, tokenizer, output_queue, abort_event, bias_tensor, top_k=5):
        self.stopping_phrases = [sp.replace("\\n", "\n") for sp in stopping_phrases]
        
        self.tokenizer = tokenizer
        self.top_k = top_k
        self.bias_tensor = bias_tensor
        
        self.output_queue = output_queue
        self.abort_event = abort_event

    def __call__(self, all_input_ids, all_scores):
        if self.abort_event.is_set():
            raise InterruptedError("client dropped connection")

        result = None

        for seqidx, input_ids in enumerate(all_input_ids):
            t = self.tokenizer.decode(input_ids.tolist(), skip_special_tokens=True)
            t_before = self.tokenizer.decode(input_ids.tolist()[:-1], skip_special_tokens=True)
            t_str = self.tokenizer.decode(input_ids.tolist()[-1], skip_special_tokens=False)

            finish_reason = "length"

            if input_ids[-1] == self.tokenizer.eos_token_id:
                finish_reason = "stop"

            # print(termcolor.colored(t[len(t_before):], "green"), end="")
            try:
                scores = all_scores[-1][seqidx]
                top_score = make_float(torch.max(scores))
                topk_scores = torch.topk(scores, self.top_k)
                topk_scores = {i:s for i, s in zip(topk_scores.indices.tolist(), topk_scores.values.tolist())}
                topk_scores[int(input_ids[-1])] = make_float(scores[input_ids[-1]])
                topk_scores = {self.tokenizer.decode([i], skip_special_tokens=True): make_float(s) for i, s in topk_scores.items()}
                # remove empty strings
                topk_scores.pop("", None)

                result_object = {
                    "id": "hf-123", 
                    "object": "text_completion", 
                    "created": time.time().as_integer_ratio()[0],
                    "choices": [
                        {
                            "text": t_str,
                            "index": seqidx,
                            "logprobs": {
                                "tokens": [t_str],
                                "token_logprobs": [top_score],
                                "top_logprobs": [
                                    topk_scores
                                ], 
                                "text_offset": [len(t_before)]
                            }, 
                            "finish_reason": finish_reason
                        }
                    ], 
                    "model": "huggingface"
                }
                data = result_object
                self.output_queue.put(data)

                # for stopping_phrase in self.stopping_phrases:
                #     last_occurence = t.rfind(stopping_phrase)
                #     if last_occurence != t_before.rfind(stopping_phrase):
                #         result = result_object
            except Exception as e:
                print("generation error", str(e), flush=True)
                import traceback
                traceback.print_exc()
            
        return False

def score(
        model,
        input_ids: torch.LongTensor,
        completion: torch.LongTensor,
        eos_token_id: Optional[int] = None,
        **model_kwargs,
    ) -> Tuple[torch.FloatTensor, torch.FloatTensor]:
        # prepare model inputs
        model_inputs = model.prepare_inputs_for_generation(torch.cat([input_ids, completion], dim=-1), **model_kwargs, eos_token_id=eos_token_id)

        token_scores = []
        
        outputs = model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, -len(completion), :]
        next_token_logits = torch.log_softmax(next_token_logits, dim=-1)
        token_scores = next_token_logits.gather(-1, completion)

        return token_scores

def log_echo(all_input_ids, all_scores, tokenizer, output_queue):
    t_before = ""

    for seqidx, (input_ids, scores) in enumerate(zip(all_input_ids, all_scores)):
        assert len(input_ids) == len(scores), "input_ids and scores must be the same length but got {} and {}".format(len(input_ids), len(scores))

        for i,score in zip(range(len(input_ids)), scores):
            tok = tokenizer.decode([input_ids[i]], skip_special_tokens=True)
            t = t_before + tok

            if i == 0 and input_ids[i] == tokenizer.bos_token_id:
                t_before = ""
                continue

            result_object = {
                "id": "hf-123", 
                "object": "text_completion", 
                "created": time.time().as_integer_ratio()[0],
                "choices": [
                    {
                        "text": t[len(t_before):],
                        "index": seqidx,
                        "logprobs": {
                            "tokens": [t[len(t_before):]],
                            "token_logprobs": [make_float(score)],
                            "top_logprobs": [
                                {
                                    t[len(t_before):]: make_float(score)
                                }
                            ], 
                            "text_offset": [len(t_before)]
                        }, 
                        "finish_reason": "length"
                    }
                ], 
                "model": "huggingface"
            }

            t_before = t
            output_queue.put(result_object)
    
async def run(input_ids, model, tokenizer, response, temperature=0.0, echo=False, num_logprobs=1, **kwargs):
    start = time.time()
    logger = None
    
    output_queue = Queue()
    abort_event = Event()

    async def logging():
        while True:
            data = output_queue.get()
            
            if data is None:
                if output_queue.empty():
                    break
                else:
                    continue
            try:
                data = json.dumps(data)
                await response.write(("data: " + data + "\n").encode("utf-8"))
            except ConnectionResetError:
                abort_event.set()
                break

    bias_tensor = None

    if "logit_bias" in kwargs and kwargs.get("logit_bias", None) is not None:
        biases = kwargs["logit_bias"]
        bias_tensor = torch.zeros(tokenizer.vocab_size)
        for k, v in biases.items():
            bias_tensor[int(k)] = v
        # print("bias tensor", bias_tensor, flush=True)
        kwargs.pop("logit_bias")
        logit_processor = lambda input_ids, scores: scores + bias_tensor    
        kwargs["logits_processor"] = [logit_processor]
    
    logger = Logger(kwargs.get("stopping_criteria", []), tokenizer, output_queue, abort_event, top_k=num_logprobs, bias_tensor=bias_tensor)
    kwargs["stopping_criteria"] = [logger]

    kwargs["stopping_criteria"] = [logger]

    # some hard-coded kwargs
    kwargs["do_sample"] = temperature != 0.0
    if temperature != 0.0:
        kwargs["temperature"] = temperature
    kwargs["num_return_sequences"] = 1
    kwargs["bos_token_id"] = tokenizer.bos_token_id
    kwargs["eos_token_id"] = tokenizer.eos_token_id
    kwargs["pad_token_id"] = tokenizer.eos_token_id
    if not "max_new_tokens" in kwargs:
        kwargs["max_new_tokens"] = 512
    kwargs["output_scores"] = True
    kwargs["return_dict_in_generate"] = True

    def _generate_task():
        try:
            # print("generate() with", kwargs, "echo =", echo, flush=True)
            if echo: 
                bos_only = torch.tensor([tokenizer.bos_token_id]).view(1,1)
                # broadcast to num input_ids
                bos_only = bos_only.repeat(len(input_ids), 1)
                scores = score(model, bos_only, torch.tensor(input_ids), **kwargs)
                log_echo(input_ids, scores.tolist(), tokenizer, output_queue)
            if kwargs.get("max_new_tokens") > 0:
                kwargs["max_new_tokens"] = max(2, kwargs["max_new_tokens"])
                # generate with max_new_tokens
                model.generate(torch.tensor(input_ids), **kwargs)
        except KeyboardInterrupt:
            pass
        except InterruptedError:
            print("client disconnected")
        except Exception as e:
            print("exception during generate()", e, flush=True)
            import traceback
            traceback.print_exc()
        output_queue.put(None)
    
    with concurrent.futures.ThreadPoolExecutor() as pool:
        logger_task = asyncio.create_task(logging())
        await asyncio.get_event_loop().run_in_executor(pool, _generate_task)
        output_queue.put(None)
        await logger_task

    # print(termcolor.colored(tokenizer.decode(input_ids, skip_special_tokens=True), "green"))
    # print("took", time.time() - start, "seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=str)
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--cuda", action="store_true", default=False)
    parser.add_argument("--dtype", type=str, default="none", help="What format to load the model weights. Options: 'float16' (not available on all models), '8bit' (requires bitsandbytes)")
    parser.add_argument("--wait_until_ready", action="store_true", default=False, help="Whether the server should start only after the model and tokenizer have been loaded.")

    args = parser.parse_args()
    model_name = args.model

    # parse dtype
    dtype = args.dtype
    load_in_8bit = dtype == "8bit"
    if dtype == "float16":
        dtype = torch.float16
    else:
        dtype = None

    # load model
    if not args.cuda:
        print("Loading {} (CPU)".format(model_name))
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, resume_download=True, load_in_8bit=load_in_8bit)
    else:
        print("Loading {} (Multi-GPU)".format(model_name))
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, resume_download=True, load_in_8bit=load_in_8bit, device_map="auto")
    model = model.eval()

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = model.eval()

    async def handle_completion(request):
        body = await request.json()

        model_name = body["model"]

        if model_name != args.model:
            res = web.Response(status=400)
            res.text = "This API serves the model " + args.model + ", but you requested " + model_name
            return res

        input_ids = []
        for p in body["prompt"]:

        # input_ids = body["prompt"][0] # input IDs
            if type(p) is str:
                input_ids += [tokenizer(input_ids)["input_ids"]]
            else:
                input_ids += [p]
    
        max_tokens = body["max_tokens"]
        temperature = body["temperature"]
        stream = body["stream"]

        if not stream:
            res = web.Response(status=400)
            res.text = "This API only supports streaming requests."
            return res

        num_logprobs = body.get("logprobs", 1)
        echo = body["echo"]
        logit_bias = body.get("logit_bias")

        response = web.StreamResponse()

        response.content_type = "text/event-stream"
        response.charset = "utf-8"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["X-Accel-Buffering"] = "no"

        await response.prepare(request)
        
        await run(input_ids, model, tokenizer, response, temperature=temperature, echo=echo,
                  max_new_tokens=max_tokens, logit_bias=logit_bias, num_logprobs=num_logprobs)

        try:
            await response.write(b"data: [DONE]")
            await response.write_eof()
        except ConnectionResetError:
            # if client has already disconnected, this will fail
            pass
        
        return response

    app = web.Application()
    app.add_routes([web.post("/completions", handle_completion)])

    def p(*print_args):
        print("[Serving mocked OpenAI API at http://" + args.host + ":" + str(args.port) + "/completions]")
    web.run_app(app, port=args.port, host=args.host, print=p)