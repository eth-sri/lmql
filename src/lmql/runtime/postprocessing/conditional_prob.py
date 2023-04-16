from lmql.runtime.decoder_head import DecoderHead
from lmql.runtime.prompt_interpreter import ProgramState

import numpy as np
from lmql.utils import nputil

class ScoringQuery:
    def __init__(self, result, scoring_head_index, prompt, values, output_writer):
        self.variable_name = result.distribution_variable
        self.result = result
        self.scoring_head_index = scoring_head_index

        self.prompt = prompt
        self.values = values
        self.output_writer = output_writer
        
        self.value_input_ids = None
        self.scores = [[] for i in range(len(values))]
        
        self.batch_idx = 0
        self.batch_size = -1

        self.log_score_prompt = False

    async def where(self, head: DecoderHead):
        if self.value_input_ids is None:
            self.value_input_ids = [await head.tokenize(v) for v in self.values]

        idx = self.batch_idx * self.batch_size + head.seq_idx 

        next_token_logits = head.next_token_logits
        next_token_logits = np.zeros_like(next_token_logits)
        
        if len(self.value_input_ids[idx]) == 0:
            head.next_token_logits[:] = np.finfo(np.float32).min
            next_token_logits[head.eos_token_id] = 100
            return next_token_logits

        head.next_token_logits[:] = np.finfo(np.float32).min
        next_token_logits[self.value_input_ids[idx][0]] = 100
        self.value_input_ids[idx] = self.value_input_ids[idx][1:]

        return next_token_logits
    
    async def rewriter(self, head: DecoderHead):
        score = nputil.log_softmax(head.next_token_logits)[head.next_token_id]
        
        idx = self.batch_idx * self.batch_size + head.seq_idx 

        if head.next_token_id != head.eos_token_id:
            self.scores[idx] += [score]
            await self.debugger_output(head)
        
        if self.log_score_prompt:
            text = await head.detokenize(head.input_ids_without_padding.reshape(-1).tolist())
            print("Scored", "\n".join(l for l in text.split("\n")[-5:]), "with", sum(self.scores[idx] + [0]))
        
        return None

    async def debugger_output(self, head):
        if self.output_writer is None: return

        idx = self.batch_idx * self.batch_size + head.seq_idx
        # more expensive but needed when there are bugs in input_id rewriting
        full_ids = head.input_ids_without_padding.reshape(-1).tolist() + [head.next_token_id]
        full_text = await head.detokenize(full_ids)
        
        value = self.values[idx]

        program_state = ProgramState()
        program_state.variable_values = self.result.variables.copy()
        program_state.variable_values[self.variable_name] = value
        program_state.variable_values[f"score({self.variable_name})"] = sum(self.scores[idx] + [0])

        self.output_writer.add_interpreter_head_state("P({} = \"{}\")".format(self.variable_name, value), self.scoring_head_index, 
            full_text, None, None, True, "fin", None, len(full_ids), program_state)


    async def score(self, model, batch_size=None):
        self.batch_size = batch_size
        if self.batch_size is None:
            self.batch_size = len(self.values)
        
        self.scores = await model.score_distribution_values(self.prompt, self.values)
        return [np.array(s) for s in self.scores]

class ConditionalDistributionPostprocessor:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.output_writer = interpreter.output_writer

    async def process(self, results):
        model = self.interpreter.model

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

            scorer = ScoringQuery(result, i, result.prompt, distribution_values, self.output_writer)
            scores = await scorer.score(model, batch_size=self.interpreter.decoder_kwargs.get("distribution_batch_size", None))

            # print("Computing P({} | {}) for result {}...".format(distribution_variable, result.prompt[:10] + "...", i))

            scores = np.stack([s.sum() for s in scores], axis=0)
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
