import os

openai_secret = None
openai_org = None

# get project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_openai_secret():
    if "LMQL_BROWSER" in os.environ:
        # get openai secret from JS context
        import js
        openai_secret = str(js.get_openai_secret())
        openai_org = str(js.get_openai_organization())
        
        return openai_secret, openai_org
    elif "LMQL_OPENAI_SECRET" in os.environ and "LMQL_OPENAI_ORG" in os.environ:
        return os.environ["LMQL_OPENAI_SECRET"], os.environ["LMQL_OPENAI_ORG"]
    elif "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"], ""
    elif any(k.startswith("OPENAI_API_KEY") for k in os.environ):
        return os.environ.get("OPENAI_API_KEY", None), ""
    else:
        search_paths = [
            os.path.join(ROOT_DIR, "api.env"),
            os.path.join(os.getcwd(), "api.env"),
            os.path.join(os.getenv("HOME"), ".lmql", "api.env")
        ]
        
        if not any(os.path.exists(p) for p in search_paths):
            m = """To use openai/<models> you have to set environment variable OPENAI_API_KEY or provide an api.env file in one of the following locations:\n\n{}\n\n To use OpenAI models you need to create an api.env file with the following contents:
        openai-secret: <your openai secret>
        openai-org: <your openai org>
        
Alternatively, you may just define the environment variable OPENAI_API_KEY=sk-...
        """.format("\n".join(" - " + p for p in search_paths))
            raise FileNotFoundError(m)

        valid_paths = [p for p in search_paths if os.path.exists(p)]

        # get openai secret from file
        with open(valid_paths[0], "r") as f:
            for line in f:
                if line.startswith("openai-secret: "):
                    openai_secret = line.split("openai-secret: ")[1].strip()
                elif line.startswith("openai-org: "):
                    openai_org = line.split("openai-org: ")[1].strip()
                    
        return openai_secret, openai_org
                
openai_secret, openai_org = get_openai_secret()