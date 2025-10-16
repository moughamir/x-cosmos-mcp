def count_tokens(text: str, model: str) -> int:
    """Count the number of tokens in a string using a simple word-based approximation.
    TODO: Replace with a proper LLM-specific tokenizer (e.g., tiktoken) for accuracy.
    """
    return len(text.split())


def tokenize(text: str, model: str) -> list[str]:
    """Tokenize a string using a simple word-based approximation.
    TODO: Replace with a proper LLM-specific tokenizer (e.g., tiktoken) for accuracy.
    """
    return text.split()


def truncate_text_to_tokens(text: str, model: str, max_tokens: int) -> str:
    """Truncate text to a specific number of tokens.
    TODO: Replace with a proper LLM-specific tokenizer (e.g., tiktoken) for accuracy.
    """
    tokens = tokenize(text, model)
    if len(tokens) > max_tokens:
        return " ".join(text.split()[:max_tokens])  # A simple approximation
    return text
