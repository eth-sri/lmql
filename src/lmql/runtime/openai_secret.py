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
    else:
        if not os.path.exists(os.path.join(ROOT_DIR, "api.env")):
            raise FileNotFoundError("""api.env not found in project root. Please create a file of the following format:
        openai-secret: <your openai secret>
        openai-org: <your openai org>
        """)

        # get openai secret from file
        with open(os.path.join(ROOT_DIR, "api.env"), "r") as f:
            for line in f:
                if line.startswith("openai-secret: "):
                    openai_secret = line.split("openai-secret: ")[1].strip()
                elif line.startswith("openai-org: "):
                    openai_org = line.split("openai-org: ")[1].strip()
                    
        return openai_secret, openai_org
                
openai_secret, openai_org = get_openai_secret()