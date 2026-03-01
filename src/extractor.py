import json
import re

import ollama

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


def parse_questions_json(raw_text: str) -> list[dict]:
    """Parse model response into a list of question dicts."""
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


def extract_questions_from_image(path: str, model: str = "llama3.2-vision") -> list[dict]:
    """Call a local Ollama vision model to extract questions from a single image."""
    response = ollama.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": VISION_PROMPT,
            "images": [path],
        }],
    )
    raw_text = response["message"]["content"]
    return parse_questions_json(raw_text)
