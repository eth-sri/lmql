import asyncio
import json
import logging
import os
import sys
import torch
import transformers
from queue import Queue
from typing import Iterator

import cog
import lmql
from lmql.models.lmtp.lmtp_scheduler import Scheduler, TokenSession
from lmql.models.lmtp.lmtp_async import LMTPAsyncTransport

logging.basicConfig()
logging.getLogger("asyncio").setLevel(logging.WARNING)

os.environ['TRANSFORMERS_OFFLINE']='1'

class Predictor(cog.BasePredictor):
    def setup(self):
        """Run initial setup to enable faster predict calls later"""
        self.model: str = "checkpoints"
        self.model_args: dict = {"device_map": "auto"}

        if os.path.exists('config.json'):
            self.model_args.update(json.load(open('config.json', 'r')))

        self.transformers_config = json.load(open('checkpoints/config.json'))
        self.torch_dtype_name = self.transformers_config.get('torch_dtype')
        if self.torch_dtype_name is not None:
            self.torch_dtype = getattr(torch, self.torch_dtype_name)
        else:
            self.torch_dtype = None

        if self.torch_dtype is not None:
            if self.model_args.get('load_in_4bit'):
                self.model_args['quantization_config'] = transformers.BitsAndBytesConfig(
                    load_in_4bit = True,
                    bnb_4bit_compute_dtype = self.torch_dtype,
                    bnb_4bit_quant_type = 'nf4',
                    bnb_4bit_use_double_quant=True,
                )

        # instantiating a scheduler puts it in the registry; we don't _really_ need to keep a reference here
        self._scheduler = Scheduler.instance(
            self.model, self.model_args, user=None, sync=False
        )

    # based on lmtp_inference_task but not using gather
    async def lmtp_inference_stream(self, ops_batch, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        token_queue = asyncio.Queue()
        transport = LMTPAsyncTransport(token_queue)
        session = TokenSession(transport, self.model_args, static=True, longrunning=True)

        next_local_id = 0
        orig_ids = {}     # tracks all ids seen, even ones that are done
        open_ids = set()  # lists only ids that are expected to still produce results
        prev_warned = set()

        try:
            for cmd, args in ops_batch:
                orig_ids[next_local_id] = args.get('stream_id')
                open_ids.add(next_local_id)
                args['stream_id'] = next_local_id
                args['model'] = 'checkpoints' # ignore specified model and substitute our own
                next_local_id += 1
                await session.handle(cmd, args) # enqueue the command

            # now, we need to retrieve results...
            while True:
                (response_type, response_data) = await token_queue.get()
                local_id = response_data.get('stream_id')
                orig_id = orig_ids.get(local_id)
                if not local_id in open_ids:
                    if not local_id in prev_warned:
                        print(f'WARNING: Ignoring extra content for {local_id!r} (formerly {orig_id!r})', file=sys.stderr)
                        prev_warned.add(local_id)
                    continue

                if response_type != 'TOKEN':
                    print(f'WARNING: Unrecognized response type {response_type!r}; may need to be updated', file=sys.stderr)

                response_data['stream_id'] = orig_id

                yield f'{response_type!s} {json.dumps(response_data)}\n'
                if response_data.get("finish_reason") is not None:
                    open_ids.discard(local_id)
                if "error" in response_data:
                    if local_id is not None:
                        # Treat this as an error only for the one stream, not the whole result
                        open_ids.discard(local_id)
                    else:
                        # an error without an id attached means we're finished
                        return
                if len(open_ids) == 0:
                    return
        finally:
            session.close()

    # Note that cog invokes this with apply_async in a multiprocessing threadpool.
    def predict(self, ops_batch_json: str) -> cog.ConcatenateIterator[str]:
        # if input doesn't parse, we want to fail fast; so do this first
        ops_batch = json.loads(ops_batch_json)

        loop = asyncio.new_event_loop()
        loop.set_debug(True)
        asyncio.set_event_loop(loop)

        gen = self.lmtp_inference_stream(ops_batch)
        try:
            while True:
                yield loop.run_until_complete(gen.__anext__())
        except StopAsyncIteration:
            return
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

if __name__ == '__main__':
    if len(sys.argv) == 2:
        request = sys.argv[1]
    else:
        request = sys.stdin.read()
    args = json.loads(request)
    p = Predictor()
    print('INFO: About to run setup()...', file=sys.stderr)
    p.setup()
    print('INFO: Finished with setup(), about to start predictions', file=sys.stderr)
    for result in p.predict(request):
        print(result, flush=True)
