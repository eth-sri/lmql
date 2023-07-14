from typing import List, Any, Union, Optional, NamedTuple

import asyncio
import numpy as np
from lmql.utils import nputil

from dataclasses import dataclass

from .dclib_global import get_tokenizer
from .dclib_array import DataArray, Continuation, topk, alpha_length_normalized, alpha_length_normalized_det

detokenize_seqs = True

@dataclass
class DecoderGraphSnapshot:
    node_hashes = None
    step_not_updated_count = None

class DecoderGraph:
    def __init__(self):
        self.nodes = {}
        self.node_ids = {}
        self.edges = []

        self.ctr = 0

        self.json_snapshot: DecoderGraphSnapshot = DecoderGraphSnapshot()

    def add_node(self, node):
        uid = f"n{self.ctr}"
        self.ctr += 1
        self.node_ids[node] = uid
        self.nodes[uid] = node
        return uid
    
    def set_pool(self, node, pool_name):
        if not self.node_ids[node] in self.nodes:
            self.add_node(node)
        self.nodes[self.node_ids[node]]["pool"] = pool_name
    
    def add_edge(self, from_node, to_node):
        self.edges.append((self.node_ids[from_node], self.node_ids[to_node]))

    async def json(self, diff: bool = False):
        nodes = []
        
        if self.json_snapshot.node_hashes is None:
            self.json_snapshot.node_hashes = {}
        if self.json_snapshot.step_not_updated_count is None:
            self.json_snapshot.step_not_updated_count = {}
        
        for k, v in self.nodes.items():
            hash = None
            if diff and k in self.json_snapshot.node_hashes:
                # this will ignore changes to nodes that have not been updated for 3 steps (may miss changes to nodes that 
                # are not updated for a long time, careful for now)
                if k in self.json_snapshot.step_not_updated_count and self.json_snapshot.step_not_updated_count[k] > 4:
                    continue
                hash = await v.json_hash()
                if self.json_snapshot.node_hashes[k] == str(hash):
                    self.json_snapshot.step_not_updated_count[k] = self.json_snapshot.step_not_updated_count.get(k, 0) + 1
                    continue
                    
                # else:
                #     print("node changed", k, self.json_snapshot.node_hashes[k], hash)
            if hash is None:
                hash = await v.json_hash()

            nodes.append({
                "id": k,
                **await v.json()
            })
            
            if diff:
                self.json_snapshot.node_hashes[k] = str(hash)
                self.json_snapshot.step_not_updated_count[k] = 0

        return {
            "nodes": nodes,
            "edges": self.edges
        }

class DecoderSequence:
    def __init__(self, input_ids_or_str, logprobs=None, deterministic=None, stop_phrase=None, predecessor=None, user_data=None, sticky_user_data_keys=None, epsilon_node=False, internal=False):
        assert all([p > DecoderSequence.truncation_threshold for p in logprobs]) if logprobs is not None else True

        if type(input_ids_or_str) == str:
            assert False, "constructing dc.seq() directly from string is not supported anymore"
        elif type(input_ids_or_str) == list:
            input_ids = np.array(input_ids_or_str)
        else:
            input_ids = input_ids_or_str
        
        assert nputil.is_array(input_ids), "input_ids must be a list or numpy array"
        self.input_ids = input_ids
        self.predecessor = predecessor
        
        # if no logprobs are provided assume logprob of 0 (prob of 1)
        if logprobs is None:
            self.logprobs = np.array([0 for _ in range(len(input_ids))])
        else: self.logprobs = logprobs
        assert len(self.logprobs) == len(self.input_ids), "Length of logprobs does not match length of inputs"

        if logprobs is None:
            self.prompt_len = len(input_ids)
        else:
            assert predecessor is not None, "Predecessor is None"
            self.prompt_len = self.predecessor.prompt_len

        self.epsilon_node = epsilon_node

        # if no deterministic is provided assume all tokens to be deterministic
        if deterministic is None: self.deterministic = np.array([True for _ in range(len(input_ids))], dtype=np.bool_)
        else: self.deterministic = deterministic

        assert self.deterministic.dtype == np.bool_

        assert len(self.deterministic) == len(self.input_ids), "Length of determinism status does not match length of inputs"

        # if no stop_phrase is provided assume no tokens to be stop_phrase
        if stop_phrase is None: self.stop_phrase = np.array([False for _ in range(len(input_ids))])
        else: self.stop_phrase = stop_phrase
        assert len(self.stop_phrase) == len(self.input_ids), "Length of stop_phrase status does not match length of inputs for {} and {}".format(self.stop_phrase, self.input_ids)

        # cache for logits when model is called with this sequence
        self.logits = None
        self.raw_logits = None

        if DecoderSequence.graph is not None:
            self.pool = None

        self.user_data = user_data
        self.sticky_user_data_keys = sticky_user_data_keys if sticky_user_data_keys is not None else set()
        # self.sticky_user_data_keys.add("head.variable")

        # alternative operation that may called to obtain a score in self.score_next_token if self.raw_logits are not available
        self.score_next_tokens_op = None

        # indicates to dc.rewrite whether this sequence can be rewritten
        self.needs_rewrite = True

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def id(self):
        if self._id is None: 
            return "<root>"
        return self._id

    def __new__(cls, *args, **kwargs):
        s = super().__new__(cls)

        setattr(s, "_id", f"s_{DecoderSequence.seq_ctr}")

        if DecoderSequence.graph is not None and not kwargs.get("internal"):
            DecoderSequence.graph.add_node(s)

            predecessor = kwargs.get("predecessor")
            if predecessor is not None:
                DecoderSequence.graph.add_edge(predecessor, s)
        
        DecoderSequence.seq_ctr += 1

        return s

    def data(self, key=None, value=None, sticky=False):
        if sticky:
            assert value is not None, "stickiness can only be set when setting a value s.data(key,value,sticky=True)"
        if value is not None:
            if self.user_data is None: self.user_data = {}
            set_path(self.user_data, key, value)
            self.sticky_user_data_keys.add(key)
            return value
        if key is None:
            return self.user_data
        return resolve_path(self.user_data, key)

    @property
    def is_query_constrained(self):
        """All regular sequences are query constrained"""
        return True

    @property
    def num_constraints(self):
        num_const = self.data('head.num_variables_decoded')
        return 0 if num_const is None else num_const

    @property
    def num_det_tokens(self):
        return self.deterministic.sum() - self.prompt_len

    @property
    def num_nondet_tokens(self):
        return (~self.deterministic).sum()

    @property
    def num_tokens(self):
        return len(self.input_ids) - self.prompt_len

    async def detokenized(self, name):
        async def seqtext_provider():
            t = str(get_tokenizer().decode(self.input_ids))
            t = str(t.encode("utf-8"))[2:-1]
            return t
        async def text_provider():
            t = str([get_tokenizer().decode(self.input_ids[-1:])])[2:-2]
            INVALID_CHARACTER = "\uFFFD"
            if INVALID_CHARACTER in t:
                # use token id
                if type(self.input_ids[-1]) is int:
                    t = "token:" + str(self.input_ids[-1])
                elif type(self.input_ids[-1]) is bytes or type(self.input_ids[-1]) is np.bytes_:
                    # best effort solution to decode multibyte characters in the UI
                    for i in range(4):
                        if not INVALID_CHARACTER in get_tokenizer().decode([self.input_ids[-i-1]]):
                            break
                        t = get_tokenizer().decode(self.input_ids[-i-1:])
                        if INVALID_CHARACTER not in t:
                            return t
                    t = ""
                    # t = str(byte_value)[2:-1]
                else:
                    t = str(self.input_ids[-1])
                    t = str(t.encode("utf-8"))[2:-1]
            return t
        providers = {
            "seqtext": seqtext_provider,
            "text": text_provider
        }
        
        if not hasattr(self, "tokenizer_cache"):
            self.tokenizer_cache = {}
        if name not in self.tokenizer_cache:
            assert name in providers, f"Unknown tokenizer cache provider {name}"
            self.tokenizer_cache[name] = await providers[name]()
        
        return self.tokenizer_cache[name]

    async def json_hash(self):
        o = await self.json()
        if type(o["user_data"]) is dict and "openai-continuations" in o["user_data"]:
            o["user_data"].pop("openai-continuations")
        return hash(str(o))

    async def json(self):
        seqtext = await self.detokenized("seqtext")
        text = await self.detokenized("text")
        if self.epsilon_node: text = [""]
        root = False
        if self.predecessor is None:
            text = await self.detokenized("seqtext")
            # text = str([await get_tokenizer().decode(self.input_ids)])[2:-2],
            root = True

        # handle empty seq
        if len(self.input_ids) == 0:
            return {
                "seq_id": self.id,
                "text": [""],
                "seqtext": "",
                "root": root,
                "logprob": [],
                "logprobs": [],
                "logprobs_det": [],
                "logprobs_norm": [],
                "seqlogprob": 0,
                **({"deterministic": True} if self.epsilon_node else {}),
                "score_det": 0,
                "score_nor": 0,
                "score_tot": 0,
                "pool": self.pool,
                "user_data": await self.user_data_json(),
                "token_id": "",
                "deterministic_5": [],
                "stop_phrase_5": [],
                "prompt_len" : self.prompt_len,
                "sticky_user_data_keys": list(self.sticky_user_data_keys)
            }

        return {
            "seq_id": self.id,
            # "input_ids": self.input_ids.tolist(),
            "text": [text],
            "seqtext": seqtext,
            "root": root,
            "logprob": self.logprobs[-1:] if len(self.logprobs) > 0 else [],
            "logprobs": self.logprobs[-5:].tolist(),
            "logprobs_det": self.logprobs[-5:][self.deterministic[-5:]].tolist(),
            "logprobs_norm": self.logprobs[-5:][~self.deterministic[-5:]].tolist(),
            "seqlogprob": self.logprobs.sum(),
            **({"deterministic": True} if self.epsilon_node else {}),
            # "score_det": alpha_length_normalized.score(self.logprobs[self.prompt_len:][self.deterministic[self.prompt_len:]], alpha=self.data("scorer_alpha")),
            # "score_nor": alpha_length_normalized.score(self.logprobs[self.prompt_len:][~self.deterministic[self.prompt_len:]], alpha=self.data("scorer_alpha")),
            "score_det": alpha_length_normalized.score(
                self.logprobs[self.prompt_len:][self.deterministic[self.prompt_len:]],),
            "score_nor": alpha_length_normalized.score(
                self.logprobs[self.prompt_len:][~self.deterministic[self.prompt_len:]]),
            "score_tot": alpha_length_normalized_det.score(self.logprobs, self),
            "pool": self.pool,
            "user_data": await self.user_data_json(),
            "token_id": self.input_ids[-1],
            "deterministic_5": self.deterministic[-5:].tolist(),
            "stop_phrase_5": self.stop_phrase[-5:].tolist(),
            "prompt_len" : self.prompt_len,
            "sticky_user_data_keys": list(self.sticky_user_data_keys)
        }

    async def user_data_json(self):
        import json
        class UserJsonEncoder(json.JSONEncoder):
            async def default(self, o):
                try:
                    if type(o) is dict:
                        return {str(k): await self.default(v) for k, v in o.items()}
                    elif type(o) is list:
                        return [await self.default(v) for v in o]
                    elif type(o) is tuple:
                        return tuple(await self.default(list(o)))
                    return super().default(o)
                except:
                    if hasattr(o, "json") and callable(o.json):
                        return await self.default(await o.json())
                    # check for NamedTuple
                    elif hasattr(o, "_asdict") and callable(o._asdict):
                        return await self.default(o._asdict())
                    elif type(o) is int:
                        return o
                    elif type(o) is float:
                        return o
                    elif type(o) is bool:
                        return o
                    else:
                        return str(o)
        return await UserJsonEncoder().default(self.user_data)

    def extend_user_data(self, continuation=None, user_data=None):
        assert continuation is None or user_data is None, f"continuation and user_data are mutually exclusive arguments"
        # prepares the user_data dictionary to use with sucessor sequences
        if continuation is None and user_data is None:
            user_data = {}
        elif continuation is not None:
            if type(continuation.user_data) is list:
                assert len(continuation.user_data) == 1, f"continuation.user_data is a list of length {len(continuation.user_data)} but should be a list of length 1"
                user_data = deepcopy(continuation.user_data[0])
            else:
                user_data = deepcopy(continuation.user_data)
        elif user_data is not None:
            user_data = deepcopy(user_data)
        else:
            user_data = deepcopy(continuation.user_data)
        for sk in self.sticky_user_data_keys:
            if user_data is None:
                user_data = {}
            set_path(user_data, sk, self.data(sk), create_missing=True, replace=False)
        return user_data

    def extend(self, continuation, internal=False):
        stop_phrase = self.detect_stop_phrase(continuation)

        return DecoderSequence(
            input_ids_or_str=np.concatenate([self.input_ids, continuation.token.reshape(1)]), 
            logprobs=np.concatenate([self.logprobs, continuation.logprob.reshape(1)]),
            # deterministic tokens are only extended in DeterministicDecoderSequence.extend.
            # So here, all extended tokens are non-deterministic, i.e. model predictions.
            deterministic=np.concatenate([self.deterministic, np.array([False])], dtype=np.bool_),
            stop_phrase=stop_phrase,
            predecessor=self,
            user_data=self.extend_user_data(continuation),
            sticky_user_data_keys=self.sticky_user_data_keys,
            internal=internal
        )

    def detect_stop_phrase(self, continuation):
        old_stop_phrase = self.stop_phrase
        new_stop_phrase = np.concatenate([old_stop_phrase, np.array([False])])
        
        stop_phrases = self.data("head").stopping_phrases["tokenized"] if self.data("head") is not None else []

        if stop_phrases is None or len(stop_phrases) == 0:
            return new_stop_phrase

        ids = np.concatenate([self.input_ids, continuation.token.reshape(1)])
        for stop in stop_phrases:
            len_stop = len(stop)
            if all(ids[-len_stop:] == stop):
                new_stop_phrase[-len_stop:] = True
                break

        return new_stop_phrase

    def __len__(self):
        return len(self.input_ids)

    def __repr__(self) -> str:
        ids = ", ".join([str(i) for i in self.input_ids[-10:]])
        return f"<seq token_len={len(self.input_ids)} ids=[... {ids}]>"

    async def text(self, offset:int=None, limit:int=None, pretty=False) -> str:
        offset = offset or 0
        limit = limit or len(self.input_ids)
        raw_text = get_tokenizer().decode(self.input_ids[offset:limit])
        
        if not pretty: 
            return raw_text
        else:
            return str([raw_text])[2:-2]

    async def str(self, full=False) -> str:
        ids = ", ".join([str(i) for i in self.input_ids[-10:]])
        if detokenize_seqs:
            s = get_tokenizer().decode(self.input_ids)
            if not full:
                s = "..." + s[-40:]
            return f"<seq token_len={len(self.input_ids)} s={str([s])[1:-1]} ids=[... {ids}]>"
        else:
            return f"<seq token_len={len(self.input_ids)} ids=[... {ids}]>"

    def __str__(self):
        ids = ", ".join([str(i) for i in self.input_ids[-10:]])
        return f"<seq token_len={len(self.input_ids)} ids=[... {ids}]>"

    def is_done(self):
        return self.input_ids[-1] == get_tokenizer().eos_token_id or \
            self.input_ids[-1] == str(get_tokenizer().eos_token_id).encode() or \
            self.input_ids[-1] == b"<|endoftext|>"

    def make_successors(self, next_tokens, next_token_scores, logits, user_data=None):
        # remove very low scoring tokens (likely they were masked and therefore score low)
        next_tokens = nputil.ensure_iterable(next_tokens)
        next_token_scores = nputil.ensure_iterable(next_token_scores)
        
        tokens = [t for t, s in zip(next_tokens, next_token_scores) if s > DecoderSequence.truncation_threshold]
        scores = [s for s in next_token_scores if s > DecoderSequence.truncation_threshold]

        if len(tokens) == 0:
            print("WARNING: all continuation token fall below truncation threshold. This is likely due to a too small truncation factor. Try increasing it. Continuing with the top 1 token.")
            tokens = [t for t, s in zip(next_tokens, next_token_scores)][:1]
            scores = [s for s in next_token_scores][:1]
        next_tokens = np.stack(tokens, axis=0)
        next_token_scores = np.stack(scores, axis=0)

        return Continuation(next_tokens, next_token_scores, user_data)
# global counter for all sequences created in this process for identification purposes
DecoderSequence.seq_ctr = 0

DecoderSequence.graph = None
# tokens with a logprob lower than this will be ignored and not expanded during decoding
DecoderSequence.truncation_threshold = -3e38

def resolve_path(d, path):
    if d is None:
        return None
    segments = path.split(".")
    for segment in segments:
        if hasattr(d, "_asdict") and callable(d._asdict):
            d = d._asdict()
        if segment not in d:
            return None
        d = d[segment]
    return d

def set_path(d, path, value, create_missing=False, replace=True):
    if d is None:
        return
    segments = path.split(".")
    for segment in segments[:-1]:
        if segment not in d:
            if create_missing:
                d[segment] = {}
            else:
                return
        d = d[segment]
    if not replace and segments[-1] in d.keys():
        return
    d[segments[-1]] = value

def deepcopy(d):
    # deepcopy dict and iterables
    if type(d) is dict:
        return {k: deepcopy(v) for k, v in d.items()}
    elif type(d) is list:
        return [deepcopy(v) for v in d]
    else:
        return d

def deepmerge(a, b):
    if a is None: return b
    if b is None: return a
    for k,v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(b[k], dict):
            deepmerge(a[k], b[k])
        else:
            a[k] = b[k]
    return a

class DeterministicDecoderSequence(DecoderSequence):
    def __init__(self, input_ids, logprobs, deterministic, stop_phrase, next_ids, next_logprobs=None, next_deterministic=None, predecessor=None, user_data=None, needs_rewrite=False, sticky_user_data_keys=None, internal=False):
        super().__init__(input_ids, logprobs, deterministic, stop_phrase, predecessor, user_data=user_data.copy() if user_data is not None else None, sticky_user_data_keys=sticky_user_data_keys, internal=internal)
        self.next_ids = next_ids
        self.next_logprobs = next_logprobs
        self.next_deterministic = next_deterministic

        self.needs_rewrite = needs_rewrite
        self.internal = internal

        if next_logprobs is not None: assert len(next_logprobs) == len(next_ids), "Length of deterministic continuation did not match length of provided logprobs. Provided logprobs: {}, Provided IDs: {}".format(len(next_logprobs), next_ids)
        if next_deterministic is not None: assert len(next_deterministic) == len(next_ids), "Length of determinism status did not match length of provided logrprobs"

        self.align_user_data()

    # async def text(self, offset: int = None, limit: int = None, pretty=True) -> str:
    #     return "<detseq> " + await super().text(offset, limit, pretty)

    def align_user_data(self):
        if self.user_data is None: return
        if not "head" in self.user_data: return

        # lmql-specific user data has to be different for deterministic sequences
        
        # make sure to update all "head" an "head[...]" user data keys (head[...] belong to subinterpreters)
        head_user_data_keys = [k for k in self.user_data.keys() if k.startswith("head[") or k == "head"]
        
        for head_key in head_user_data_keys:
            head_variable = resolve_path(self.user_data, f"{head_key}.variable")
            
            if head_variable is not None:
                # deterministic sequences don't have stopping phrases
                set_path(self.user_data, head_key, self.user_data[head_key].updated(stopping_phrases={"tokenized": [], "text": []}))
            else:
                set_path(self.user_data, head_key, self.user_data[head_key].updated(variable="<prompt>"))
            
            if len(self.next_ids) > 0:
                set_path(self.user_data, head_key, self.user_data[head_key].updated(mask="{token_id=" + str(self.next_ids[0]) + "}"))
            else:
                set_path(self.user_data, head_key, self.user_data[head_key].updated(mask="<not available yet>"))

    @property
    def is_query_constrained(self):
        """Deterministic sequences are not query constrained, as long as they are fixed to their predetermined content."""
        return True if len(self.next_ids) == 0 else False

    async def json(self):
        seqtext = await self.detokenized("seqtext")
        text = await self.detokenized("text")
        root = False
        if self.predecessor is None:
            text = await self.detokenized("seqtext")
            # text = str([await get_tokenizer().decode(self.input_ids)])[2:-2],
            root = True
        
        return {
            "seq_id": self.id,
            # "input_ids": self.input_ids.tolist(),
            "text": [text],
            "seqtext": seqtext,
            "root": root,
            "logprob": self.logprobs[-1],
            "seqlogprob": self.logprobs.sum(),
            "pool": self.pool,
            **({"deterministic": True} if self.deterministic[-1] else {}),
            "next_ids": self.next_ids.tolist(),
            "next_logprobs": self.next_logprobs.tolist() if self.next_logprobs is not None else None,
            "user_data": await self.user_data_json(),
            "token_id": self.input_ids[-1],
            "deterministic_5": self.deterministic[-5:].tolist(),
            "stop_phrase_5": self.stop_phrase[-5:].tolist(),
            "score_det": alpha_length_normalized.score(self.logprobs[self.prompt_len:][self.deterministic[self.prompt_len:]]),
            "score_nor": alpha_length_normalized.score(self.logprobs[self.prompt_len:][~self.deterministic[self.prompt_len:]]),
            "score_tot": alpha_length_normalized_det.score(self.logprobs, self),
            **({"done": True} if self.data("head.variable") == "__done__" else {}),
            "sticky_user_data_keys": list(self.sticky_user_data_keys)
        }

    def expand(self, limit=None):
        """ Returns the sequence that corresponds to the full expansion of this pre-determined deterministic sequence. """
        s = self
        steps = 0
        while type(s) is DeterministicDecoderSequence and len(s.next_ids) > 0 and (limit is None or steps < limit):
            s = s.extend(Continuation(s.next_ids[0], s.next_logprobs[0], s.user_data))
        return s

    def extend_user_data(self, continuation=None, user_data=None):
        # additionally add self.user_data for deterministic sequence extensions
        return deepmerge(deepcopy(self.user_data), super().extend_user_data(continuation=continuation, user_data=user_data))

    def extend(self, continuation, internal=False):
        # if not more predetermined tokens are left, just extend as usual and return a regular seq()
        if len(self.next_ids) <= 0:
            return super().extend(continuation)

        assert continuation.token == self.next_ids[0], "deterministic sequences must be extended by the predetermined next token: provided: " + str(continuation.token) + ", predetermined: " + str(self.next_ids[0])

        extended_input_ids = np.concatenate([self.input_ids, continuation.token.reshape(1)])
        extended_logprobs = np.concatenate([self.logprobs, continuation.logprob.reshape(1)])
        extended_deterministic = np.concatenate([self.deterministic, np.array([True]) if self.next_deterministic is None else self.next_deterministic[0:1]], dtype=np.bool_)

        reduced_next_ids = self.next_ids[1:]
        reduced_next_logprobs = self.next_logprobs[1:] if self.next_logprobs is not None else None
        reduced_deterministic = None if self.next_deterministic is None else self.next_deterministic[1:]

        user_data = self.extend_user_data(continuation)

        stop_phrase = self.detect_stop_phrase(continuation)
        if self.data("injected_stop_phrase"):
            assert not extended_deterministic[-1]

        return DeterministicDecoderSequence(
            input_ids=extended_input_ids, 
            logprobs=extended_logprobs, 
            deterministic=extended_deterministic,
            stop_phrase=stop_phrase,#np.concatenate([self.stop_phrase, self.data("injected_stop_phrase")]),
            next_ids=reduced_next_ids,
            next_logprobs=reduced_next_logprobs,
            next_deterministic=reduced_deterministic,
            predecessor=self, 
            user_data=user_data,
            needs_rewrite=self.needs_rewrite,
            sticky_user_data_keys=self.sticky_user_data_keys,
            internal=internal or self.internal
        )

    def __repr__(self) -> str:
        ids = ", ".join([str(i) for i in self.input_ids[-10:]])
        if (len(self.next_ids) > 0): 
            ids = "... " + ids
        next_ids = ", ".join([str(i) for i in self.next_ids[:10]])
        if len(self.next_ids) > 10: 
            next_ids = "..." + next_ids
        return f"<detseq token_len={len(self.input_ids)} ids=[{ids}] next_ids=[{next_ids}]>"

    async def str(self, full=False) -> str:
        ids = ", ".join([str(i) for i in self.input_ids[-10:]])
        if (len(self.next_ids) > 0): 
            ids = "... " + ids
        next_ids = ", ".join([str(i) for i in self.next_ids[:10]])
        if len(self.next_ids) > 10: 
            next_ids = "..." + next_ids
        if detokenize_seqs:
            s = get_tokenizer().decode(self.input_ids)
            if not full:
                s = "..." + s[-40:]
            return f"<detseq token_len={len(self.input_ids)} s={str([s])[1:-1]} ids=[{ids}] next_ids=[{next_ids}]>"
        else:
            return f"<detseq token_len={len(self.input_ids)} ids=[{ids}] next_ids=[{next_ids}]>"

    def make_successors(self, next_tokens, next_token_scores, logits, user_data=None):
        # if no more predetermined tokens are left, just make successors as usual
        if len(self.next_ids) <= 0:
            return super().make_successors(next_tokens, next_token_scores, logits, user_data=user_data)

        # logits here are unprocessed
        raw_logits = logits
        # TODO: using the raw token score will not consider sampling temperature (but it should?)
        # e.g. deterministic tokens are scored according to their raw logprob, not their logprob after temperature is applied
        # ignore next_tokens and next_token_scores, only produce predetermined next_ids as only successors
        predetermined_token = self.next_ids[0]
        
        # obtain score (either precomputed or via the passed logits)
        if self.next_logprobs is not None:
            score = self.next_logprobs[0]
        else:
            score = raw_logits[predetermined_token]
            if score < DecoderSequence.truncation_threshold:
                print("warning: a deterministic token scored below the truncation threshold ({})".format(DecoderSequence.truncation_threshold))
        
        return Continuation(predetermined_token, score, user_data)
    
    def __str__(self) -> str:
        ids = ", ".join([str(i) for i in self.input_ids[-10:]])
        return f"<detseq token_len={len(self.input_ids)} ids=[... {ids}] next_ids=[{self.next_ids[:10]}]>"

def is_deterministic(s):
    return issubclass(type(s), DeterministicDecoderSequence)

def next_is_deterministic(s):
    return is_deterministic(s) and len(s.next_ids) > 0

def is_lmql_valid(s):
    return s.data("head.valid") != False or s.data("head.final") != "fin"

def set_record_graph():
    DecoderSequence.graph = DecoderGraph()

def set_truncation_threshold(threshold):
    DecoderSequence.truncation_threshold = threshold

def detseq(
    ids: np.ndarray,
    logprobs: np.ndarray,
    deterministic: np.ndarray,
    stop_phrase: np.ndarray,
    next_ids: List[int],
    next_logprobs: List[float] = None,
    next_deterministic: Optional[np.ndarray] = None,
    predecessor=None, 
    user_data=None,
    needs_rewrite=True,
    sticky_user_data_keys=None,
    internal=False):
    
    return DeterministicDecoderSequence(
        input_ids=ids, 
        logprobs=logprobs, 
        deterministic=deterministic,
        stop_phrase=stop_phrase,
        next_ids=next_ids,
        next_logprobs=next_logprobs,
        next_deterministic=next_deterministic,
        predecessor=predecessor, 
        user_data=user_data,
        needs_rewrite=needs_rewrite,
        sticky_user_data_keys=sticky_user_data_keys,
        internal=internal
    )

def seq(ids: List[int], logprobs:Optional[np.ndarray]=None, deterministic:Optional[np.ndarray]=None):
    return DecoderSequence(ids, logprobs=logprobs, deterministic=deterministic)

def named(seqs: List[DecoderSequence] = None, name=None):
    for s in seqs:
        if hasattr(s, "pool"):
            s.pool = name
    return seqs

class FinishException(Exception):
    def __init__(self, result_sequences: List[DecoderSequence]):
        super().__init__()
        self.result_sequences = result_sequences

def finish(ar: Union[DataArray, List[DecoderSequence], DecoderSequence], **kwargs):
    """
    Terminates the decoding process and returns the provided (array of) sequences as the final
    result sequences in order of the underlying array/list. 1
    """
    if type(ar) is DecoderSequence:
        raise FinishException([ar])
    elif type(ar) is list:
        raise FinishException(ar)
    else:
        raise FinishException(list(ar.flatten().sequences.values())[0])

def token_unique(ar: DataArray, prefer=None, flatten=False):
    """
    Like unique() but compares tokens instead of sequence identities.
    """
    if prefer is None:
        prefer = lambda s,t: True

    if flatten:
        original_shape = ar.shape
        ar = ar.flatten()

    def op_unique(sqs):
        assert type(sqs) is list, f"token_unique expects a DataArray of lists of DecoderSequences, but got {type(sqs)} as data item."
        assert len(sqs) == 0 or issubclass(type(sqs[0]), DecoderSequence), f"token_unique expects a DataArray of lists of DecoderSequences, but got a list of {type(sqs[0])} as data item."

        by_token_ids = {}
        for s in sqs:
            token_ids = tuple(s.input_ids.tolist())
            curr = by_token_ids.get(token_ids, None)
            if curr is None or prefer(s, curr):
                by_token_ids[token_ids] = s
        return list(by_token_ids.values())

    res = ar.element_wise(op_unique)

    if flatten:
        return res.reshape(original_shape)
    else:
        return res


def repeat(ar, n, scorer=None):
    """
    Repeats the sequences in `ar` until a total of `n` sequences are in the array. 
    
    If no integer-valued multiple of ar's contents fit, only the top n sequences are repeated in the last tile.
    """
    if len(ar) == n: return ar
    elif len(ar) > n: 
        return topk(ar, n, scorer=scorer)
    else: 
        return ar + repeat(ar, n - len(ar), scorer=scorer)
