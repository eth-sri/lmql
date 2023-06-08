from lmql.runtime.stats import Stats

class DcGlobal: pass
DcGlobal.tokenizer = None

stats = Stats("dclib")

def get_tokenizer():
    return DcGlobal.tokenizer

def clear_tokenizer():
    DcGlobal.tokenizer = None

def set_dclib_tokenizer(tokenizer):
    assert DcGlobal.tokenizer is None or DcGlobal.tokenizer.name == tokenizer.name, f"Cannot set dclib tokenizer to {tokenizer.name} because it is already set to {DcGlobal.tokenizer.name} (cannot use multiple tokenizers in the same process for now)"
    DcGlobal.tokenizer = tokenizer
    
def get_tokenizer():
    return DcGlobal.tokenizer