import os
import tempfile
from lmql.tests.expr_test_utils import run_all_tests
import subprocess
import sys
import os
import time
import shutil

"""
This test only works with Azure valid credentials.

As AZURE_DEPLOYMENT, please provide a valid model deployment name.
"""
AZURE_API_BASE = os.environ.get("AZURE_API_BASE", None)
AZURE_API_KEY = os.environ.get("AZURE_API_KEY", None)
AZURE_DEPLOYMENT = os.environ.get("AZURE_DEPLOYMENT", "gpt-35-turbo")

LMQL_FILE = f"""
argmax "Hello[WHO]" from "openai/{AZURE_DEPLOYMENT}" where len(TOKENS(WHO)) < 2
"""

async def test_missing_api_type():
    # this will try to use openai.com with Azure credentials
    await run_with_env_vars(AZURE_API_KEY, AZURE_API_BASE, None, "Incorrect API key provided")

async def test_all_valid():
    await run_with_env_vars(AZURE_API_KEY, AZURE_API_BASE, "azure-chat", None)

async def test_no_base():
    await run_with_env_vars(AZURE_API_KEY, None, "azure-chat", "Please specify the Azure API base URL as 'api_base' or environment variable OPENAI_API_BASE")

async def test_no_key():
    await run_with_env_vars(None, AZURE_API_BASE, "azure-chat", "Please specify the Azure API key as 'api_key' or environment variable OPENAI_API_KEY or OPENAI_API_KEY_<DEPLOYMENT>")

async def test_model_valid():
    await run_with_lmql_model(AZURE_API_BASE, "azure-chat", AZURE_API_KEY, None)

async def test_model_invalid_key():
    await run_with_lmql_model(AZURE_API_BASE, "azure-chat", "invalid-key", "Access denied due to invalid subscription key or wrong API endpoint.")

async def test_model_invalid_base():
    await run_with_lmql_model("https://doesnotexist404123.openai.azure.com/", "azure-chat", AZURE_API_KEY, "Cannot connect to host")

async def test_base_missing():
    await run_with_lmql_model(None, "azure-chat", AZURE_API_KEY, "Please specify the Azure API base URL")

async def test_key_missing():
    await run_with_lmql_model(AZURE_API_BASE, "azure-chat", None, "Please specify the Azure API key as 'api_key' or environment variable")

async def test_key_via_env():
    await run_with_lmql_model(AZURE_API_BASE, "azure-chat", None, None, extra_env={"OPENAI_API_KEY": AZURE_API_KEY})

async def test_key_via_env_deployment():
    await run_with_lmql_model(AZURE_API_BASE, "azure-chat", None, None, extra_env={"OPENAI_API_KEY_" + AZURE_DEPLOYMENT.upper(): AZURE_API_KEY})

async def test_key_via_env_wrong_deployment():
    await run_with_lmql_model(AZURE_API_BASE, "azure-chat", None, "Please specify the Azure API key as 'api_key' or environment variable", extra_env={"OPENAI_API_KEY_WRONG_" + AZURE_DEPLOYMENT.upper(): AZURE_API_KEY})


async def run_with_lmql_model(api_base, api_type, api_key, expected_error, extra_env = {}):
    model_name = 'openai/' + AZURE_DEPLOYMENT
    api_key_mapping = f"api_key=\"{api_key}\"" if api_key is not None else ""
    api_base_mapping = f"api_base=\"{api_base}\", " if api_base is not None else ""
    model_str = f'lmql.model("{model_name}", api_type="{api_type}", {api_base_mapping} {api_key_mapping})'

    lmql_file = f"""
    argmax "Hello[WHO]" from {model_str} where len(TOKENS(WHO)) < 2
    """

    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.update(extra_env)

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        try:
            with open("f.lmql", "w") as f:
                f.write(lmql_file.strip())

            assert_output_has_error(["lmql", "run", "f.lmql"], expected_error, env=env)
        finally:
            # remove f.lmql
            os.remove("f.lmql")

async def run_with_env_vars(api_key, api_base, api_type, expected_error):
    with tempfile.TemporaryDirectory() as tmpdir:
        with open("f.lmql", "w") as f:
            f.write(LMQL_FILE.strip())

        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)

        if api_key is not None:
            env["OPENAI_API_KEY"] = api_key
        
        if api_type is not None:
            env["OPENAI_API_TYPE"] = api_type

        if api_base is not None:
            env["OPENAI_API_BASE"] = api_base

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
                return
        
        # get exit code
        p.wait()
        if expected_error is None:
            assert p.returncode == 0, "Expected process to exit with code 0, but got {} with output:\n\n{}".format(p.returncode, output)
        else:
            assert has_error, "Expected process output to contain '{}', but got {}".format(expected_error, output)
            assert p.returncode != 0, "Expected process to exit with non-zero code, but got {}".format(p.returncode)
        

if __name__ == "__main__":
    if AZURE_API_BASE is None or AZURE_API_KEY is None:
        print("Skipping Azure tests because AZURE_API_BASE and AZURE_AZURE_API_KEY are not set")
        sys.exit(0)

    run_all_tests(globals())