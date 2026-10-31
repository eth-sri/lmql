import numpy as np

from lmql.models.lmtp.backends.llama_cpp_model import LlamaCppModel
from lmql.tests.expr_test_utils import run_all_tests


def test_logits_processors():
    model = object.__new__(LlamaCppModel)
    input_ids = np.array([0])
    scores = np.zeros(3)

    for bias, expected in [
        ({1: np.log(3)}, [0.2, 0.6, 0.2]),
        ({}, [1 / 3, 1 / 3, 1 / 3]),
    ]:
        processors = model.logits_processors([bias])
        np.testing.assert_allclose(np.exp(processors(input_ids, scores)), expected)

        processed = scores.copy()
        for processor in processors:
            processed = processor(input_ids, processed)
        np.testing.assert_allclose(np.exp(processed), expected)


def test_empty_logits_processors():
    model = object.__new__(LlamaCppModel)
    assert model.logits_processors([]) == []


if __name__ == "__main__":
    run_all_tests(globals())
