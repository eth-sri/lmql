from typing import Tuple
import os

# get project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_MISSING_CREDS_ERROR_MSG_TEMPLATE = """\
To use openai/<models>, you have to configure your API credentials. To do so
you can either define the `OPENAI_API_KEY` environment variable or create a
file `api.env` in one of the following locations:

{search_paths}

To use OpenAI models you need to create an api.env file with the following
contents:
        
        openai-secret: <your openai secret>
        openai-org: <your openai org>
        
For more info, check the related project docs:
https://docs.lmql.ai/en/stable/language/openai.html#configuring-openai-api-credentials
"""


def _get_secret_from_browser() -> Tuple[str, str]:
    if "LMQL_BROWSER" not in os.environ:
        raise ValueError("No LQM_BROWSER value in env variables")
    # get openai secret from JS context
    import js

    openai_secret = str(js.get_openai_secret())
    openai_org = str(js.get_openai_organization())
    return openai_secret, openai_org


def _get_secret_from_env() -> Tuple[str, str]:
    openai_org = os.environ.get("LMQL_OPENAI_ORG", "")
    if "LMQL_OPENAI_SECRET" in os.environ:
        openai_secret = os.environ["LMQL_OPENAI_SECRET"]
    elif "OPENAI_API_KEY" in os.environ:
        openai_secret = os.environ["OPENAI_API_KEY"]
    else:
        raise ValueError("OpenAI API secret not found in env variables")
    
    return openai_secret, openai_org


def _get_secret_from_file() -> Tuple[str, str]:
    search_paths = [
        os.path.join(ROOT_DIR, "api.env"),
        os.path.join(os.getcwd(), "api.env"),
        os.path.join(os.getenv("HOME"), ".lmql", "api.env"),
    ]

    if not any(os.path.exists(p) for p in search_paths if p is not None):
        m = _MISSING_CREDS_ERROR_MSG_TEMPLATE.format(
            search_paths="\n".join(" - " + p for p in search_paths if p is not None)
        )
        raise FileNotFoundError(m)

    valid_paths = [p for p in search_paths if os.path.exists(p)]

    openai_secret = None
    # openai_org is optional
    openai_org = None
    lines = []

    # get openai secret from file
    with open(valid_paths[0], "r") as f:
        for line in f:
            lines += [line]
            if line.startswith("openai-secret: "):
                openai_secret = line.split("openai-secret: ")[1].strip()
            elif line.startswith("openai-org: "):
                openai_org = line.split("openai-org: ")[1].strip()

    assert openai_secret is not None, "No 'openai-secret: ' entry found in api.env file:\n\n{}".format("".join(lines))

    return openai_secret, openai_org


def get_openai_secret() -> Tuple[str, str]:
    try:
        return _get_secret_from_browser()
    except ValueError:
        pass

    try:
        return _get_secret_from_env()
    except ValueError:
        pass

    return _get_secret_from_file()


openai_secret, openai_org = get_openai_secret()
