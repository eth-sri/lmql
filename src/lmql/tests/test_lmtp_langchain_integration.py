import lmql
import pytest
import sys

from lmql.models.lmtp.lmtp_langchain import LMTP
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

@pytest.fixture(scope="module", name="test_llm")
def instantiate_test_llm():
    return LMTP(
        # The model below can be replaced with any other model
        # result is not important; would love to use "random"
        model="random",
        temperature=1.7,
        max_length=10
    )

# setup to run lmql serve-model
@pytest.fixture(scope="module", autouse=True)
def run_lmql_serve_model():
    import subprocess
    p = subprocess.Popen(["lmql", "serve-model", "random", "--seed", "123"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    yield p

# teardown to stop lmql serve-model
@pytest.fixture(scope="module", autouse=True)
def stop_lmql_serve_model(run_lmql_serve_model):
    yield
    run_lmql_serve_model.terminate()

ARGS = ("## Intro: The",)
KWARGS = {"stop": ["\n", "\\.", "Wonders"]}

@pytest.mark.asyncio
async def test_do_async(test_llm):
    r = await test_llm.apredict(*ARGS, **KWARGS)
    assert r == "available Spoon announces 1929edyame fertilizer Dipmmseasea", "apredict result is not as expected"


@pytest.mark.asyncio
async def test_do_sync_in_async(test_llm):
    with pytest.raises(RuntimeError):
        test_llm.predict(*ARGS, **KWARGS)


def test_do_sync(test_llm):
    r = test_llm.predict(*ARGS, **KWARGS)
    assert r == "available Spoon announces 1929edyame fertilizer Dipmmseasea", "predict result is not as expected"

if __name__ == "__main__":
    # only run this file with pytest
    sys.exit(pytest.main(args=["-s", __file__]))