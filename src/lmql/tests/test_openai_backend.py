import os
import tempfile
from lmql.tests.expr_test_utils import run_all_tests
import subprocess
import sys
import os

LMQL_FILE = """
argmax "Hello[WHO]" from "openai/text-ada-001" where len(TOKENS(WHO)) < 2
"""

"""
This test only works with openai.com valid credentials
as provided by the environment variables OPENAI_API_KEY and OPENAI_ORG
"""
API_KEY = os.environ.get("OPENAI_API_KEY", None)
API_ORG = os.environ.get("OPENAI_ORG", None)

async def test_invalid_api():
     await run_with_api_env("abc", "org-abc", "Incorrect API key provided")

async def test_invalid_org():
    await run_with_api_env(API_KEY, "org-abc", "No such organization: org-abc.")

async def test_both_valid():
    await run_with_api_env(API_KEY, API_ORG, None)

async def test_no_org():
    await run_with_api_env(API_KEY, None, None)

async def test_no_api():
    await run_with_api_env(None, None, "No 'openai-secret: ' entry found in api.env file")

async def test_env_no_api():
    await run_with_env_vars(None, None, "file `api.env` in one of the following locations")

async def test_env_no_org():
    await run_with_env_vars(API_KEY, None, None)

async def test_env_both_valid():
    await run_with_env_vars(API_KEY, API_ORG, None)

async def test_env_invalid_org():
    await run_with_env_vars(API_KEY, "org-abc", "No such organization: org-abc.")

async def test_env_invalid_api():
    await run_with_env_vars("abc", "org-abc", "Incorrect API key provided")

async def test_env_invalid_api_and_org():
    await run_with_env_vars("abc", "org-abc", "Incorrect API key provided")

async def run_with_api_env(api_key, org, expected_error):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        with open("api.env", "w") as f:
            if api_key is not None:
                f.write("openai-secret: {}\n".format(api_key))
            if org is not None:
                f.write("openai-org: {}\n".format(org))

        with open("f.lmql", "w") as f:
            f.write(LMQL_FILE.strip())

        env = os.environ.copy()

        env.pop("OPENAI_API_KEY", None)

        assert_output_has_error(["lmql", "run", "f.lmql"], expected_error, env=env)

async def run_with_env_vars(api_key, org, expected_error):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        with open("f.lmql", "w") as f:
            f.write(LMQL_FILE.strip())

        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)

        if api_key is not None:
            env["OPENAI_API_KEY"] = api_key
        if org is not None:
            env["LMQL_OPENAI_ORG"] = org

        assert_output_has_error(["lmql", "run", "f.lmql"], expected_error, env=env)


def assert_output_has_error(cmd, expected_error, env):
        env["HOME"] = "."
        
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        has_error = False
        output = ""
        
        for line in list(p.stdout) + list(p.stderr):
            line = line.decode("utf-8").strip()
            output += line + "\n"
            if expected_error is not None and expected_error in line:
                has_error = True
                p.terminate()
        
        # print(output)

        # get exit code
        p.wait()
        if expected_error is None:
            assert p.returncode == 0, "Expected process to exit with code 0, but got {} with output:\n{}".format(p.returncode, output)
        else:
            assert has_error, "Expected process output to contain '{}', but got {}".format(expected_error, output)
            assert p.returncode != 0, "Expected process to exit with non-zero code, but got {}".format(p.returncode)
        

if __name__ == "__main__":
    # the above but for API_KEY and API_ORG
    if API_KEY is None or API_ORG is None:
        print("test_openai_backend.py: Skipping OpenAI API configuration tests because OPENAI_API_KEY and OPENAI_ORG are not set")
        sys.exit(0)

    run_all_tests(globals())