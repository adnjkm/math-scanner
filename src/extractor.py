import json
import re

import ollama

VISION_PROMPT = """You are a math question extractor. Your response must be ONLY a JSON array — no explanation, no markdown, no code fences, no extra text before or after.

Identify every distinct numbered or lettered exercise on this textbook page. Output a JSON array where each element is an object with these exact keys:
  "number": the exercise label as shown (e.g. "1", "2a", "b")
  "text": plain-text version of the question
  "latex": the question with all math notation in LaTeX ($...$ for inline, $$...$$ for display)
  "space_cm": integer — estimated cm of blank space needed to solve by hand:
    4  = simple 1-step problem
    7  = multi-step (3-5 steps)
    12 = multi-part or complex
    15 = proof or very long
    6  = default if unsure

Example output format (do not copy this content, only follow this structure):
[{"number":"1","text":"Find the derivative of x^2","latex":"Find the derivative of $x^2$","space_cm":4}]

Return ONLY the JSON array. No other text."""


def parse_questions_json(raw_text: str) -> list[dict]:
    """Parse model response into a list of question dicts, tolerating extra text."""
    text = raw_text.strip()

    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Try to extract a JSON array from anywhere in the response
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        text = match.group(0)

    questions = json.loads(text)

    if not isinstance(questions, list):
        raise ValueError(f"Expected a JSON array, got: {type(questions).__name__}\nRaw: {raw_text[:300]}")

    validated = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue  # skip stray strings or non-objects
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
