import re


def clean_html(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"\\s+", " ", text)
    return text.strip()


def shorten(text: str, max_len=2000) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text
