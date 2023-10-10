import GPT3Tokenizer from 'gpt3-tokenizer';

const tokenizer = new GPT3Tokenizer({ type: 'gpt3' }); // or 'codex'

function tokenize_gpt_toks(line) {
    let input_ids = tokenize_gpt(line);
    return input_ids.map(i => tokenizer.decodings[i])
}

function tokenize_gpt(line) {
    if (line == "<|endoftext|>") {
        return [50256];
    }
    // assert that no other occurences of eos
    if (line.includes("<|endoftext|>")) {
        throw "Invalid input: " + line;
    }
    const encoded  = tokenizer.encode(line);
    return encoded["bpe"];
}

function detokenize_gpt(input_ids) {
    const decoded = tokenizer.decode(input_ids);
    return decoded;
}

function get_vocab() {
    return tokenizer.encodings;
}

function convert_tokens_to_string_gpt(tokens) {
    return tokenizer.decode(tokens);
}

self.tokenize_gpt = tokenize_gpt
self.tokenize_gpt_toks = tokenize_gpt_toks
self.get_vocab = get_vocab
self.detokenize_gpt = detokenize_gpt
self.convert_tokens_to_string_gpt = convert_tokens_to_string_gpt