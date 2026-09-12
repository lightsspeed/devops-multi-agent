def extract_text(content) -> str:
    """
    Convert LangChain/Gemini response content into plain text.

    Gemini may return:
    - a plain string
    - a list of content blocks
    """

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")

                if text:
                    text_parts.append(text)

        return "\n".join(text_parts).strip()

    return str(content).strip()