from typing import List, Dict, Union
import numpy as np
import asyncio
from lmql.model.client import ServedPretrainedModel
from lmql.runtime.hf_integration import transformers_model

from .dclib_model import model

from dataclasses import dataclass

class TrieNode:
    def __init__(self, id: int, logits: Union[List[float], Dict[int, float]]):
        self.id = id
        self.children = {}
        self.logits = logits

    def sequences(self, prefix):
        if len(self.children) == 0:
            return [prefix + [self.id]]
        else:
            return [seq for child in self.children.values() for seq in child.sequences(prefix + [self.id])]

    def set_logits(self, logits):
        self.logits = logits

    def add_child(self, id: int, score: float, logits: Union[List[float], Dict[int, float]]):
        if id not in self.children:
            self.children[id] = TrieNode(id, logits)
            self.logits[id] = score
        else:
            self.children[id].logits = logits

        return self.children[id]

@dataclass
class SequenceCache:
    scores: List[float]
    logits: np.ndarray # (seq_len, vocab_size)
    ids: List[int]

    node: TrieNode # the node that corresponds 

    def __str__(self):
        return "SequenceCache(scores={}, logits={}, ids={})".format(self.scores, self.logits.shape, self.ids)
    
    def __repr__(self):
        return self.__str__()

class TrieCachedModel:
    def __init__(self, model, start_token_id):
        self.root = TrieNode(start_token_id, None)
        self.model = model
    
    async def score(self, input_ids: np.ndarray, *args, **kwargs):
        result, continuation = self.find_closest(input_ids)
        assert len(result.scores) == len(result.logits) == len(result.ids) - 1
        if len(continuation) == 0:
            return result.scores, result.logits

        input_ids = np.array(result.ids).reshape(1,-1)
        continuation = np.array(continuation).reshape(1,-1)

        print("scoring", input_ids, continuation)
        scores, logits = await self.model.score(input_ids, continuation, *args, **kwargs)
        node = result.node
        for i,s,l in zip(continuation[0], scores[0].numpy(), logits[0].numpy()):
            node.set_logits(l)
            node = node.add_child(i, s, None)

        return scores[0].numpy(), logits[0].numpy()

    def sequences(self):
        return self.root.sequences([])

    def find_closest(self, ids: List[int]):
        node = self.root
        ids_so_far = [self.root.id]
        remaining_ids = ids.copy()
        
        scores = []
        logits = []

        def stack(logits):
            if len(logits) == 0: return np.array([])
            else: return np.stack(logits, axis=0)

        while len(remaining_ids) > 0:
            i = remaining_ids.pop(0)
            ids_so_far.append(i)
            
            if i not in node.children:
                return SequenceCache(scores, stack(logits), ids_so_far[:-1], node), [i] + remaining_ids
            
            scores.append(node.logits[i])
            logits.append(node.logits)
            node = node.children[i]
        
        return SequenceCache(scores, stack(logits), ids_so_far, node), []
    
    def find(self, ids: List[int]):
        node, ids_so_far, remaining_ids = self.find_closest(ids)
        assert len(ids_so_far) == len(ids) and len(remaining_ids) == 0, "TrieCachedModel.find: no node found for ids {}".format(ids)
        return node

async def main():
    hf_model = transformers_model("http://localhost:8080", "gpt2-medium")()
    dcmodel = model(hf_model, bos_token_id=hf_model.bos_token_id, eos_token_id=hf_model.eos_token_id)
    cached_model = TrieCachedModel(hf_model.served_model, hf_model.bos_token_id)

    async def score(text):
        input_ids = await hf_model.tokenize(text)
        print(text)
        return await cached_model.score(input_ids)
        
    print(await score("Hello World"))
    print(await score("Hello There"))
    print(await score("Hello Out There"))
    print(await score("Hello World"))

    print(cached_model.sequences())

if __name__ == "__main__":
    asyncio.run(main())