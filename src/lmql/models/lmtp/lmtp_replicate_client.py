"""
This file contains a client for tunneling LMTP over Replicate's protocol.
"""

import aiohttp
import aiohttp_sse_client.client
import asyncio
import json
import os
import sys
import warnings
from .errors import LMTPStreamError

class LMTPReplicateClient:
    """
    Simple client for tunneling LMTP into Replicate (https://replicate.com/)
    """
    def __init__(self, model_identifier, session, endpoint, **kwargs):
        if 'REPLICATE_API_TOKEN' in os.environ:
            self.api_key = os.environ['REPLICATE_API_TOKEN']
        else: # FIXME: Allow API key to be passed in kwargs?
            raise Exception('Please define REPLICATE_API_TOKEN as an environment variable to use Replicate models')

        endpoint = endpoint.removeprefix('replicate:')
        if len(endpoint) == 0:
            endpoint = model_identifier
        endpoint_pieces = endpoint.split('/')

        if len(endpoint_pieces) == 2:
            # only passed a name without a version
            self.model_identifier = endpoint
            self.model_version = None
        elif len(endpoint_pieces) == 3:
            # passed a name/version pair
            self.model_identifier = '/'.join(endpoint_pieces[:2])
            self.model_version = endpoint_pieces[-1]
        else:
            raise Exception('Unknown endpoint descriptor for replicate; should be owner/model or owner/model/version')

        self.model_validated = False
        self.session = session
        self.stream_id = 0
        self.handler = None

    async def check_model(self):
        if self.model_validated:
            return

        if not self.model_version:
            async with self.session.get(f'https://api.replicate.com/v1/models/{self.model_identifier}',
                    headers={
                        'Authorization': f'Token {self.api_key}',
                        'Content-Type': 'application/json'
                    },
            ) as resp:
                if resp.status != 200:
                    explanation = await resp.text()
                    raise Exception(f'Unhandled error: model lookup of {self.model_identifier} failed with status {resp.status}: {explanation}')
                lookup_result = await resp.json()
                self.model_version = lookup_result['latest_version']['id']
                if self.model_version is None:
                    raise Exception(f'Lookup of model {self.model_identifier} did not return a latest_version')
            self.model_validated = True
            return

        # We have identifier and version; just need to make sure they actually exist
        async with self.session.get(f'https://api.replicate.com/v1/models/${self.model_identifier}/versions/${self.model_version}',
                    headers={
                        'Authorization': f'Token {self.api_key}',
                        'Content-Type': 'application/json'
                    },
            ) as resp:
                if resp.status != 200:
                    explanation = await resp.text()
                    raise Exception(f'Unhandled error: model lookup of {self.model_identifier} version ${self.model_version} failed with status {resp.status}: {explanation}')

        self.model_validated = True


    async def submit_batch(self, batch):
        if self.model_version is None or not self.model_validated:
            await self.check_model()
        # FIXME: Maybe store id to use for later cancel calls?
        body = {"input": {"ops_batch_json": json.dumps(batch)}, "stream": True, "version": self.model_version}
        async with self.session.post('https://api.replicate.com/v1/predictions',
                headers={
                    'Authorization': f'Token {self.api_key}',
                    'Content-Type': 'application/json'
                }, json=body) as resp:
            if resp.status != 201:
                explanation = await resp.text()
                raise Exception(f'Unhandled error: prediction creation failed with status {resp.status}: {explanation}')
            creation_result = await resp.json()
            stream_url = creation_result['urls']['stream'] # note there's also a cancel url provided
        async with aiohttp_sse_client.client.EventSource(stream_url,
                session=self.session,
                headers={
                    'Accept': 'text/event-stream',
                    'Authorization': f'Token {self.api_key}',
                }) as event_source:
            async for event in event_source:
                if event.type == 'done':
                    return
                content = event.data.rstrip('\n').split('\n')
                for line in content:
                    if len(line) == 0:
                        continue
                    if not ' ' in line:
                        warnings.warn(f'Misformatted content received from Replicate task: {line!r}')
                        continue
                    cmd, item_json = line.split(' ', 1)
                    if cmd != 'TOKEN' and cmd != 'MSG':
                        warnings.warn(f"Unknown command {cmd!r} in line {line!r} -- protocol version mismatch? {cmd!r}")
                        continue
                    item = json.loads(item_json)
                    if item.get("error") is not None:
                        # FIXME: Is it appropriate for this to kill the whole batch, not just the single stream?
                        raise LMTPStreamError(item["error"])
                    yield item

                    # messages are single-item streams
                    if cmd == "MSG":
                        break

    async def request(self, name, payload):
        """
        Requests metadata about the configuration 
        of the currently running model.
        """
        self.stream_id += 1
        payload = {
            "stream_id": self.stream_id,
            "model": self.model_identifier,
            "data": payload
        }
        async for result in self.submit_batch([[name, payload]]):
            return result

        raise ValueError(f"Request {name} failed to return a result")

    async def generate(self, prompt, **kwargs):
        self.stream_id += 1
        payload = {
            **kwargs,
            "model": self.model_identifier,
            "prompt": prompt,
            "stream_id": self.stream_id
        }
        if payload.get("logit_bias", None) is None:
            payload.pop("logit_bias", None)
        async for result in self.submit_batch([["GENERATE", payload]]):
            yield result

    async def score(self, prompt, scored_prompt, **kwargs):
        self.stream_id += 1
        payload = {
            **kwargs,
            "model": self.model_identifier,
            "prompt": prompt,
            "scored": scored_prompt,
            "stream_id": self.stream_id
        }
        async for result in self.submit_batch([["SCORE", payload]]):
            yield result
