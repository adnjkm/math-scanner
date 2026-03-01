import base64
import json
import re
from pathlib import Path

import anthropic

VISION_PROMPT = """You are a math question extractor. Identify every distinct numbered/lettered exercise on this textbook page. Return ONLY a valid JSON array with no explanation, no markdown fences. Each object has:
  "number": as shown (e.g. "1", "2a")
  "text": plain-text version
  "latex": full question with all math in LaTeX ($...$ inline, $$...$$ display)
  "space_cm": integer cm of blank space needed to solve by hand:
    4  = simple 1-step derivative/limit
    7  = integration, chain/product rule (3-5 steps)
    12 = multi-part, implicit differentiation, related rates
    15 = very complex or proof-style
    6  = default if unsure"""


def encode_image_base64(path: str) -> tuple[str, str]:
    """Return (base64_str, media_type) for an image file."""
    suffix = Path(path).suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "image/png")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def parse_questions_json(raw_text: str) -> list[dict]:
    """Parse Claude's response into a list of question dicts."""
    # Strip markdown code fences if present
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    questions = json.loads(text)

    if not isinstance(questions, list):
        raise ValueError("Expected a JSON array of questions")

    validated = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise ValueError(f"Question {i} is not an object")
        number = str(q.get("number", str(i + 1)))
        text_val = str(q.get("text", ""))
        latex = str(q.get("latex", text_val))
        space_cm = int(q.get("space_cm", 6))
        validated.append({
            "number": number,
            "text": text_val,
            "latex": latex,
            "space_cm": space_cm,
        })

    return validated


def extract_questions_from_image(path: str, api_key: str) -> list[dict]:
    """Call Claude Vision to extract questions from a single image."""
    client = anthropic.Anthropic(api_key=api_key)
    image_data, media_type = encode_image_base64(path)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": VISION_PROMPT,
                    },
                ],
            }
        ],
    )

    raw_text = message.content[0].text
    return parse_questions_json(raw_text)
