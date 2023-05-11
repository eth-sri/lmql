from builtins import str

import regex

from gpt3_tokenizer._functions import (_DEFAULT_ENCODING, _bpe,
                                       _bytes_to_unicode, _dict_zip,
                                       _encode_string, _get_bpe_merges,
                                       _init_encoder)

_bpe_merges = _get_bpe_merges()
_bpe_ranks = _dict_zip(_bpe_merges, range(0, len(_bpe_merges)))
_REGEX_PATTERN = r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"
_encoder = _init_encoder()
_decoder = {v: k for k,v in _encoder.items()}
_byte_encoder = _bytes_to_unicode()
_byte_decoder = {v: k for k,v in _byte_encoder.items()}

def encode(text):
    """ 
        Transforms a string into an array of tokens 
        :param text: string to be encoded
        :type text: str
        :returns: an array of ints (tokens)
    """
    if not isinstance(text, str):
        text = text.decode(_DEFAULT_ENCODING)    
    bpe_tokens = []
    regex_compiled = regex.compile(_REGEX_PATTERN, regex.UNICODE)
    matches = regex_compiled.findall(text)
    for token in matches:
        token = ''.join([_byte_encoder[x] for x in _encode_string(token)])
        new_tokens = [_encoder[x] for x in _bpe(token, _bpe_ranks).split(' ')]
        bpe_tokens.extend(new_tokens)
    return bpe_tokens

def decode(tokens):
    """ 
        Transforms back an array of tokens into the original string
        :param tokens: an array of ints
        :type tokens: list
        :returns: the original text which was encoded before
    """
    text = ''.join([_decoder[x] for x in tokens])
    textarr = [int(_byte_decoder[x]) for x in list(text)]
    text = bytearray(textarr).decode("utf-8")
    return text

def count_tokens(text):
    """ 
        Returns an integer representing the tokens count of a given string 
        :param text: string to count tokens from
        :type text: str
        :returns: int representing the tokens count
        
    """
    encoded = encode(text)
    return len(encoded)
