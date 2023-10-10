"""
This file contains a list of hard-coded model information 
for LMQL to enable ready-to-use configuration for models
that have been tested and verified to work with LMQL.
"""
from dataclasses import dataclass

@dataclass
class ModelInfo:
    is_chat_model: bool = False

def model_info(model_identifier):
    if model_identifier == "openai/gpt-3.5-turbo-instruct" or model_identifier == "gpt-3.5-turbo-instruct":
        return ModelInfo(is_chat_model=False)
    elif model_identifier == "openai/gpt-4" or model_identifier == "gpt-4":
        return ModelInfo(is_chat_model=True)
    elif "gpt-3.5-turbo" in model_identifier:
        return ModelInfo(is_chat_model=True)
    else:
        return ModelInfo(is_chat_model=False)