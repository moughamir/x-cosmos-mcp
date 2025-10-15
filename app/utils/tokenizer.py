import tiktoken

def truncate_text_to_tokens(text: str, model: str, max_tokens: int) -> str:
    """Truncate text to a specific number of tokens."""
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        return encoding.decode(tokens)
    return text