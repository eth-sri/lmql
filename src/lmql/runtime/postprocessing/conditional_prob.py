import asyncio

import numpy as np

import lmql.runtime.dclib as dc
from lmql.utils import nputil

class ConditionalDistributionPostprocessor:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.output_writer = interpreter.output_writer

    async def score(self, prompt: str, values, dcmodel: dc.DcModel):
        prompt_seq = dc.seq(dcmodel.tokenizer.tokenize(prompt, asbytes=True))
        value_ids = [dcmodel.tokenizer.tokenize(value, asbytes=True) for value in values]

        dcmodel.log_billable_tokens(sum(len(ids) + 1 for ids in value_ids) + len(value_ids) * (len(prompt_seq.input_ids)))
        dcmodel.log_queries(sum(len(ids) + 1 for ids in value_ids))

        value_scores = []

        scoring_results = await dcmodel.score([prompt_seq] * len(value_ids), value_ids)
        for s, value in zip(scoring_results, value_ids):
            s = s.expand()
            value_score = s.logprobs[-len(value):]
            value_scores.append(value_score)

        return [np.array(s) for s in value_scores]

    async def process(self, results):
        model: dc.DcModel = self.interpreter.dcmodel

        if type(results) is not list:
            results = [results]

        # check if distribution is required
        if not any(r is not None and hasattr(r, "distribution_variable") and r.distribution_variable is not None for r in results):
            return results

        if len(results) > 1:
            if "top1_distribution" in self.interpreter.decoder_kwargs and self.interpreter.decoder_kwargs["top1_distribution"]:
                print("top1_distribution: only computing conditional distribution for the top1 result")
                results = [results[0]]
            else:
                print("warning: more than one result, computing conditional distribution for all of them.")

        for i, result in enumerate(results):
            if result is None: continue

            distribution_variable = result.distribution_variable
            distribution_values = result.distribution_values

            prompts = [result.prompt + value for value in distribution_values]

            if distribution_variable is None:
                print("warning: result {} has no distribution variable set even though a DISTRIBUTION clause is given".format(i))
                continue

            scores = await self.score(result.prompt, distribution_values, model)

            # print("Computing P({} | {}) for result {}...".format(distribution_variable, result.prompt[:10] + "...", i))

            scores = np.stack([s.mean() for s in scores], axis=0)
            log_probs = nputil.log_softmax(scores)
            probs = np.exp(log_probs)
            
            distribution = [(value, prob, prompt) for value, prob, prompt in zip(distribution_values, probs, prompts)]
            log_distribution = [(value, log_prob, prompt) for value, log_prob, prompt in zip(distribution_values, log_probs, prompts)]

            result.variables[distribution_variable] = max(distribution, key=lambda x: x[1])[0]
            result.prompt = max(distribution, key=lambda x: x[1])[2] # get prompt including distribution value for argmax result
            
            result.variables[f"P({distribution_variable})"] = [(value, prob) for value, prob, _ in distribution]
            result.variables[f"log P({distribution_variable})"] = [(value, prob) for value, prob, _ in log_distribution]

        if len(results) == 1:
            return results[0]
        else:
            return results
