import asyncio
import numpy as np
from typing import List, Any, Union, Optional, Dict

from lmql.runtime.tokenizer import load_tokenizer
from lmql.runtime.dclib.dclib_array import DataArray, sum_scorer, alpha_length_normalized, alpha_length_normalized_det
from lmql.runtime.dclib.dclib_seq import next_is_deterministic
import lmql.runtime.dclib as dc
from lmql.runtime.stats import Stats

@dc.decoder
async def argmax(prompt_ids: np.ndarray, n=1, max_len=2048, **kwargs):
    model = dc.model(**kwargs)
    h = dc.seqs([dc.seq(prompt_ids)] * n)
    done = dc.seqs()
    step = 0
    
    # provide early first result to user
    yield h

    while len(h) > 0:
        h = h.extend(await model.argmax(h, noscore=True))
        h = await model.rewrite(h, noscore=True)
        h, done = (h + done).separate_by(dc.logical_not(dc.eos), dc.lt(max_len))
        
        step += 1

        yield (h, done)

    dc.finish(done)


@dc.decoder
async def my_argmax(prompt_ids: np.ndarray, n=1, max_len=2048, **kwargs):
    model = dc.model(**kwargs)
    h = dc.seqs([dc.seq(prompt_ids)] * 1)
    done = dc.seqs()
    step = 0
    
    # provide early first result to user
    yield h

    while len(h) > 0:
        # extend current hypothesis with top-k continuations
        h = h.extend(await model.topk_continuations(h, k=4, **kwargs))
        # check logprob of each continuation
        for s in h.items():
            print(s.logprobs[-1], flush=True)
        # select top-1 continuation only
        h = dc.topk(h, 1)
        
        print(h, flush=True)
        h = await model.rewrite(h, noscore=True)
        h, done = (h + done).separate_by(dc.logical_not(dc.eos), dc.lt(max_len))
        
        step += 1

        yield (h, done)

    dc.finish(done)

@dc.decoder
async def sample(prompt_ids: np.ndarray, temperature=1, n=1, max_len=2048, **kwargs):
    model = dc.model(**kwargs)
    h = dc.seqs([dc.seq(prompt_ids)] * n)
    done = dc.seqs()

    while len(h) > 0:
        h = h.extend(await model.sample(h, temperature=temperature, noscore=True))
        h = await model.rewrite(h, noscore=True)
        h, done = (h + done).separate_by(dc.logical_and(dc.logical_not(dc.eos), dc.lt(max_len)))

        yield (h, done)
    
    yield (h, done)

    dc.finish(done)


@dc.decoder
async def best_k(prompt_ids: np.ndarray, k=4, budget=30, kappa=1, beta=0.5, gamma=0.05, max_heap_size=500, top_k_continuations=5, max_len=None, **kwargs):

    class BestKScorer(dc.topk_scorer):
        def __init__(self, base_scorer, t=0, kappa=1, beta=0.5, *args, **kwargs):
            self.t = t
            self.kappa = kappa
            self.beta = beta
            self.base_scorer = base_scorer

        def __call__(self, scores, s):
            def decay(time):
                return -self.kappa*(self.t - time)**self.beta
            time = s.data('time')
            if time is None: time = -1
            return self.base_scorer(scores)+decay(time)

    def prefer_older(s, t):
        if s is None: return False 
        if t is None: return True 
        st = s.data('time')
        tt = s.data('time')
        if st is None: return False
        if tt is None: return True
        if st < tt: return True

    model = dc.model(**kwargs)
    # keep track of active beams and finished sequences
    h = dc.seqs([dc.seq(prompt_ids)] * 1)
    h.data('time', -1)
    done = dc.seqs()

    t = 0
    T = 0

    base_scorer = dc.alpha_length_normalized()
    while T < budget and len(h) > 0 or len(done) == 0:
        scorer = BestKScorer(base_scorer, t, kappa, beta)
        H, h = dc.seperate_topk(h, k, scorer=scorer)
        g = len(H)
        H = H.extend(await model.topk_continuations(H, k=top_k_continuations, **kwargs))
        H = await model.rewrite(H)
        not_done = dc.logical_and(dc.logical_not(dc.eos), dc.lt(max_len))
        H, H_done = H.separate_by(not_done)
        # print(len(H), len(H_done))
        done = (done + H_done)
        H = H.filter(lambda s: np.exp(s.logprobs[-1]) >= gamma)
        H.data('time', t)
        h = dc.token_unique((h + H), prefer=prefer_older)
        h = dc.topk(h, max_heap_size, scorer=scorer)

        t += 1
        T += g
        yield (h, done)
    
    done = dc.topk(done, len(done))
    done.name("final result")
    dc.finish(done)

@dc.decoder
async def beam_sample(prompt_ids: np.ndarray, n=4, max_len=None, temperature=None, **kwargs):
    n = kwargs.get("num_beams", n)
    max_len = max_len or 2048
    model = dc.model(**kwargs)
    temperature = temperature or 1.0

    # keep track of active beams and finished sequences
    h = dc.seqs([dc.seq(prompt_ids)] * 1)
    done = dc.seqs()

    # stopping criteria for the beam search
    not_done = dc.logical_and(dc.logical_not(dc.eos), dc.lt(max_len))

    for num_steps in range(0, max_len):
        if len(h) == 0: break

        h = h.extend(await model.sample(h, num_samples=n, temperature=temperature))
        h = await model.rewrite(h)
        h, done = (h + done).separate_by(not_done)

        h = dc.topk(h, n, name = "h_" + str(num_steps))
        done = dc.topk(done, n, name = "done_" + str(num_steps))

        # stop when done already tracks topk results
        if len(done) == n and (len(h) == 0 or dc.max_score(h) < dc.min_score(done)):
            break

        yield (h, done)
    
    yield (h, done)

    dc.finish(done)

@dc.decoder
async def beam_search(prompt_ids: np.ndarray, n=4, max_len=None, **kwargs):
    n = kwargs.get("num_beams", n)
    max_len = max_len or 2048
    model = dc.model(**kwargs)

    # keep track of active beams and finished sequences

    h = dc.seqs([dc.seq(prompt_ids)] * 1)
    done = dc.seqs()

    # stopping criteria for the beam search
    not_done = dc.logical_and(dc.logical_not(dc.eos), dc.lt(max_len))

    for num_steps in range(0, max_len):
        if len(h) == 0: break

        h = h.extend(await model.topk_continuations(h, k=n, **kwargs))
        h = await model.rewrite(h)
        h, done = (h + done).separate_by(not_done)

        h = dc.topk(h, n, name = "h_" + str(num_steps))
        done = dc.topk(done, n, name = "done_" + str(num_steps))

        # stop when done already tracks topk results
        if len(h) == 0 or (len(done) == n and dc.max_score(h) < dc.min_score(done)):
            break

        yield (h, done)
    
    dc.finish(done)

    yield (h, done)

dc.decoder(beam_search, "beam")

@dc.decoder
async def beam_var(prompt_ids: np.ndarray, n=4, max_len=None, inject_stop=False, prune=None, return_first=False, **kwargs):
    s = Stats("beam_var")

    n = kwargs.get("num_beams", n)
    max_len = max_len or 2048
    model = dc.model(**kwargs)
    alpha = kwargs.get("alpha", 0.7)
    scorer = alpha_length_normalized_det(alpha=alpha)

    # keep track of active beams and finished sequences
    s_initial = dc.seq(prompt_ids)
    s_initial.data("scorer_alpha", alpha, sticky=True)

    h = dc.seqs([s_initial] * 1)
    done = dc.seqs()

    # stopping criteria for the beam search
    not_done = dc.logical_and(dc.logical_not(dc.eos), dc.lt(max_len))

    num_completed = 0

    for num_steps in range(0, max_len):
        if len(h) == 0: break

        with s.timer("det_ext"):
            # generate deterministic parts until a variable is encountered
            det, non_det = h.separate_by(dc.next_is_deterministic)
            while len(det) > 0:
                det = det.extend(await model.argmax(det))
                det = await model.rewrite(det)
                det, non_det = (non_det + det).separate_by(dc.next_is_deterministic)

            h = non_det
            h, done_new = (h + done).separate_by(not_done)
            num_completed += len(done_new) - len(done)
            done = done_new

        h_before_extension = h
        h_extended = h.extend(await model.topk_continuations(h, k=n, **kwargs))

        if inject_stop:
            h_injected = await h_before_extension.aelement_wise(stop_phrase_injection, model, **kwargs)
            h_extended = (h_injected + h_extended)
            h_extended_shape = h_extended.shape
            h_extended = dc.token_unique(h_extended, lambda s, t: dc.is_deterministic(s), flatten=True)
            h_extended = h_extended.reshape(h_extended_shape)

        h = await model.rewrite(h_extended)
        h, done_new = (h + done).separate_by(not_done)
        num_completed += len(done_new) - len(done)
        done = done_new

        if len(done) >= 1 and prune is not None:
            # sscorer = alpha_length_normalized()
            sscorer = sum_scorer()
            ref_score = dc.max_score(done, sscorer) * prune
            det_h, nondet_h = h.separate_by(dc.is_deterministic)
            nondet_h, pruned = nondet_h.separate_by(lambda s: sscorer(s.logprobs, s) > ref_score)
            h = det_h + nondet_h
            print(f"Pruning in step {num_steps} with score {ref_score:.3f}, removed {len(pruned)}")

        # stopping criteria
        if len(h) == 0 or num_completed >= 2*n or (len(done) >= n and dc.max_score(h, scorer=scorer) < dc.min_score(done, scorer=scorer)):
            break

        # additionally pool by variable
        h = h.reshape("head.variable")

        with s.timer("allocation"):
            # keep only topk per pool in h and done
            det_h, nondet_h = h.separate_by(dc.is_deterministic)
            if len(nondet_h) > 0:
                nondet_h = post_vilar_allocation(nondet_h, n, scorer=scorer, num_steps=num_steps)
            h = det_h + nondet_h
            # h = post_vilar_allocation(h, n, scorer=scorer, num_steps=num_steps)

            done = dc.topk(done, n, scorer=scorer, name="done_" + str(num_steps))

        if len(done) > 0 and return_first:
            break

        yield (h, done)
    
    done.name("final result")
    yield done

    # sort done by score
    dc.finish(dc.array_sorted(done.flatten(), key=lambda s: -s.logprobs.sum()))


def post_vilar_allocation(h, k, scorer=None, num_steps=0):
    """
    Restricts h to a set of candidate sequences according to the criteria in Post 
    and Vilar (Fast Lexically Constrained Decoding with Dynamic Beam Allocation for Neural Machine Translation)

    Paper: http://arxiv.org/abs/1804.06609
    
    Choose candidates according to these rules:
    - keep the best top k sequences across all dimensions of h
    - keep all deterministically extended sequences
    - for each sequence of the previous step, keep at least the best continuation
    
    """
    original_shape = h.shape

    # extract deterministic sequences, including stop phrase insertions if active
    det_h, nondet_h = h.separate_by(dc.is_deterministic)
    det_h.name(f"constraint_cont_{num_steps}", nopath=True)

    # Get single best continuation of every sequence
    continuations_by_predecessor = h.reshape(lambda s: s.predecessor.id)
    best_cont_per_predecessor = dc.topk(continuations_by_predecessor, 1, scorer=scorer)
    best_cont_per_predecessor = best_cont_per_predecessor.name(f"best_cont_{num_steps}", nopath=True)
    # best_cont_per_predecessor = dc.topk(best_cont_per_predecessor, k, scorer=scorer).name(f"best_cont_{num_steps}", nopath=True)

    # Get the k best overall sequences
    h_top_k = dc.topk(h.flatten(), k, scorer=scorer)
    h_top_k = h_top_k.reshape(*original_shape).name(f"topk_{num_steps}")

    h_pool = dc.token_unique((h_top_k + det_h + best_cont_per_predecessor).flatten(), lambda s, t: dc.is_deterministic(s))

    # Filter by comparing among sequences satisfying the same number of constraints.
    num_constraints = np.array([s.num_constraints for s in h_pool.unstructured()])
    num_constraints = {det_len: (num_constraints == det_len).sum() for det_len in set(num_constraints.tolist())}


    # print("\nStep Number: ", num_steps)
    beam_size_constrained = 1*k
    bank_sizes = get_bank_sizes_post_vilar(num_constraints, beam_size_constrained)

    pools_by_const_num = h_pool.separate_by_list(lambda s: s.num_constraints)
    h_filtered = DataArray({})
    for num_const, seqs in pools_by_const_num.items():
        seqs_filtered = dc.topk(seqs, bank_sizes[num_const], scorer=scorer).name(f"bank_{num_steps}_{num_const}")
        assert all([s.num_constraints == num_const for s in seqs_filtered.unstructured()])
        h_filtered += seqs_filtered

    h = h_filtered.reshape(*original_shape)

    return h


def get_bank_sizes_post_vilar(num_seq_with_constraints: Dict[int, int],
                   beam_size: int):
    """
    First assign each bank, corresponding to a number of satisfied constraints the same number of slots,
    with the remainder going to the one for the most satisfied constraints. Then, redistribute slots of
    oversized banks downward.
    """

    num_constraints = sorted(list(num_seq_with_constraints.keys()))
    num_banks = len(num_constraints)
    bank_size = beam_size // num_banks
    remainder = beam_size - bank_size * num_banks

    bank_sizes = {det_len: bank_size for det_len in num_constraints}
    bank_sizes[num_constraints[-1]] += remainder

    bank_size_keys = sorted(list(bank_sizes.keys()))

    # reallocate oversized banks
    # print("pre: ", bank_sizes)
    roll_over = 0
    for n_const in bank_size_keys:
        bank_sizes[n_const] += roll_over
        roll_over = 0
        overfill = bank_sizes[n_const] - (num_seq_with_constraints[n_const] if n_const in num_seq_with_constraints else 0)
        if overfill > 0:
            bank_sizes[n_const] -= overfill
            roll_over += overfill

    # print("mid: ", bank_sizes)

    for n_const in reversed(bank_size_keys):
        bank_sizes[n_const] += roll_over
        roll_over = 0
        overfill = bank_sizes[n_const] - (num_seq_with_constraints[n_const] if n_const in num_seq_with_constraints else 0)
        if overfill > 0:
            bank_sizes[n_const] -= overfill
            roll_over += overfill

    # print("post: ", bank_sizes)
    assert sum(bank_sizes.values()) <= beam_size, f"Beam size {beam_size}, total banks: {sum(bank_sizes.values())}"
    return bank_sizes

async def stop_phrase_injection(seqs, model, **kwargs):
    seqs_extended = []

    for s in seqs:
        stop_phrases = s.data("head.stopping_phrases.tokenized")
        if stop_phrases is None or len(stop_phrases) == 0: continue
        if next_is_deterministic(s): continue
        if s.data("injected_stop_phrase"): continue # do not extend in a stop phrase

        for stop_phrase in stop_phrases:
            stop_phrase = np.array(stop_phrase).reshape(-1)
            # consider detseq of stop phrase
            stop_phrase_seq = await model.score(s, stop_phrase)
            # allows to distinguish between stop phrase insertions and normal continuations
            stop_phrase_seq.data("injected_stop_phrase", True)
            seqs_extended.append(stop_phrase_seq)
    return seqs_extended

class shared:
    def __init__(self, v):
        self.v = v
    def set(self, v):
        self.v = v
    def get(self):
        return self.v
    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"shared({self.v})"

class non_rewritten_score(dc.topk_scorer):
    def __init__(self, alpha=0.7):
        self.alpha = alpha

    def __call__(self, scores, s, *args, **kwargs):
        return self.score(scores, self.alpha, s)

    @classmethod
    def score(cls, scores, alpha, s, **kwargs):
        return s.data("eos_score")
        # print("eos_score", s.data("eos_score"))
        # if len(scores) == 0:
        #     return torch.tensor(0.0)
        # else:
        #     return (torch.tensor(1.0) / float(len(scores[:-1])) ** alpha) * scores[:-1].sum()


async def topk_var_continuations(model, seqs: dc.DataArray, active_variable, b, method: str, **kwargs):
    """
    model: model to use for scoring
    seqs: sequences to extend
    active_variable: active variable that should be decoded
    b: number of continuation candidates to generate per sequence
    """
    active = seqs.reshape(lambda s: s.id)
    variable_done = dc.seqs()
    active_variable.set(None)
    sample = method == "sample"

    def is_active_variable(s):
        v = s.data("head.variable")
        if v is None: return False
        if active_variable.get() is None: 
            active_variable.set(v)
            return True
        return v == active_variable.get()

    temperature = kwargs.get("temperature", 1.0)

    if method == "beam":
        i = 0

        while not is_seq_beams_search_done(active, variable_done, num_beams=b):
            # inner variable decoding (beam_sample with 2*n beams and branching factor n)
            if sample:
                active = active.extend(await model.sample(active, temperature=temperature, num_samples=b))
            else:
                kwargs.pop("temperature", None)
                active = active.extend(await model.topk_continuations(active, k=b, **kwargs))
            
            active = await model.rewrite(active)

            active, variable_done = (active + variable_done).separate_by(is_active_variable)
            active = dc.topk(active, b)

            active.name(str(active_variable.get()) + "[" + str(i) + "]_")
            i += 1
            
            yield active
    elif method == "beam_seq":
        i = 0

        regular_scorer = alpha_length_normalized()
        nw_score = non_rewritten_score()
        top_variable_done = dc.seqs()

        while not (len(active) == 0 or (len(top_variable_done) == b and dc.max_score(active, scorer=nw_score) < dc.min_score(top_variable_done, scorer=nw_score))):
            # inner variable decoding (beam_sample with 2*n beams and branching factor n)
            if sample:
                active = active.extend(await model.sample(active, temperature=temperature, num_samples=b))
            else:
                kwargs.pop("temperature", None)
                active = active.extend(await model.topk_continuations(active, k=b, **kwargs))
            
            for s in active.flatten().items():
                # s.data("eos_score", s.score
                s.data("eos_score", regular_scorer(s.logprobs))

            active = await model.rewrite(active)

            active, variable_done = (active + variable_done).separate_by(is_active_variable)
            active = dc.topk(active, b)

            top_variable_done, _ = dc.seperate_topk(variable_done, b, scorer=regular_scorer)

            active.name(str(active_variable.get()) + "[" + str(i) + "]_")
            i += 1
            
            yield active
    elif method == "sample":
        active = active.element_wise(lambda s: s.copy() * b)
        i = 0

        while not is_seq_beams_search_done(active, variable_done, num_beams=b):
            active = active.extend(await model.sample(active, temperature=temperature, num_samples=1))
            
            active = await model.rewrite(active)
            
            active, variable_done = (active + variable_done).separate_by(is_active_variable)
            active = dc.topk(active, b)

            active.name(str(active_variable.get()) + "[" + str(i) + "]_")
            i += 1

            yield active

    # final result should be token unique
    yield dc.token_unique(variable_done)

@dc.decoder
async def bsseq(prompt_ids: np.ndarray, b=2, max_len=384, **kwargs):
    kwargs.pop("n", None)
    async for s in var(prompt_ids, b=b, n=1, max_len=max_len, subdecoder="beam_seq", **kwargs):
        yield s

@dc.decoder
async def var(prompt_ids: np.ndarray, b=2, n=None, max_len=384, subdecoder="sample", temperature=1.0, return_first=False, **kwargs):
    """
    sample: 
        if True, uses beam_sample variable-local-decoding, otherwise uses beam_search-like decoding
    var_temperature: 
        sampling temperature to use to obtain multiple variable values
    """
    model = dc.model(**kwargs)
    kwargs.update({"temperature": temperature})

    # keep track of active beams and finished sequences
    variable_done = dc.seqs([dc.seq(prompt_ids)])
    active_variable = shared(None)
    done = dc.seqs()
    is_not_done = dc.logical_and(dc.logical_not(dc.eos), dc.lt(max_len))

    n_variable = 0
    # keep same number of beams as branching factor
    if n is None: n = b

    while True:
        # remove sequences that violate constraints
        # variable_done, _ = variable_done.separate_by(dc.is_lmql_valid)
        # if len(variable_done) == 0: break
        
        # generate variable continuation
        async for variable_done in topk_var_continuations(model, variable_done, active_variable, b, subdecoder, **kwargs):
            yield variable_done
        
        # restrict to top b best variable continuations
        variable_done = variable_done.flatten()
        variable_done, done = (done + variable_done).separate_by(is_not_done)
        if len(variable_done) == 0: break

        variable_done = dc.topk(variable_done, b)

        # generate deterministic parts until a variable is encountered
        det, non_det = variable_done.separate_by(dc.next_is_deterministic)
        while len(det) > 0:
            det = det.extend(await model.argmax(det))
            det = await model.rewrite(det)
            det, non_det = (det + non_det).separate_by(dc.next_is_deterministic)
            
            yield (det, non_det)

        # if after deterministic expansion all sequences are done, we are done
        variable_done, done = (det + non_det + done).separate_by(is_not_done)
        
        if len(variable_done) == 0: break

        variable_done = dc.topk(variable_done, n)
        variable_done.name("candidates_" + active_variable.get())

        yield variable_done

        if len(done) > 0 and return_first: break
        # variable_done = non_det

    done = dc.topk(done, len(done))
    done.name("final result")
    yield done
    
    dc.finish(dc.array_sorted(done.flatten(), key=lambda s: -s.logprobs.sum()))

def is_seq_beams_search_done(active_hypotheses, done_hypotheses, num_beams, scorer=None):
    return len(active_hypotheses) == 0 or (len(done_hypotheses) == num_beams and dc.max_score(active_hypotheses, scorer=scorer) < dc.min_score(done_hypotheses, scorer=scorer))

@dc.decoder
def incontext(*args, **kwargs):
    raise NotImplementedError("incontext is not a valid decoder function for standalone use")