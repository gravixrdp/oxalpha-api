import re

def sanitize_brand_text(text: str) -> str:
    brand = "Gravix AI"
    text = re.sub(r"(?i)\box\s*alpha\b", brand, text)
    text = re.sub(r"(?i)\boxalpha\.com\b", "gravix.ai", text)
    text = re.sub(r"(?i)\boxalpha\b", brand, text)
    text = re.sub(r"(?i)\bglm(?:\s*-\s*[\d\.]+(?:-flash)?)?\b", brand, text)
    text = re.sub(r"(?i)\bzhipu(?:\s*ai)?\b", "Gravix", text)
    return text

def test_sliding_buffer():
    chunks = ["Hello! I", "'m ", "Ox", " Alpha", ", an AI reasoning model. How can I help", " you?"]
    buffer = ""
    emitted = []

    for c in chunks:
        buffer += c
        sanitized = sanitize_brand_text(buffer)
        if len(sanitized) > 16:
            to_emit = sanitized[:-12]
            buffer = sanitized[-12:]
            emitted.append(to_emit)

    if buffer:
        emitted.append(sanitize_brand_text(buffer))

    full_output = "".join(emitted)
    print("Full Output:", full_output)
    assert "Ox Alpha" not in full_output
    assert "Gravix AI" in full_output
    print("TEST PASSED!")

if __name__ == "__main__":
    test_sliding_buffer()
