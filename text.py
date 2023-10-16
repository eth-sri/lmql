import os
os.environ["OPENAI_API_KEY"] = "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"

argmax
    "Write a story about testing:[RESPONSE]" where STOPS_AT(RESPONSE, "\n")

    "Write a story about testing:[RESPONSE]" where len(TOKENS(RESPONSE)) < 1024
from
    "text"