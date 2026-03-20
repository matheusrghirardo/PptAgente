"""Agent module: uses OpenAI to generate slide content for a given topic."""

import json
import os

from openai import OpenAI


def generate_slides(topic: str, num_slides: int = 5) -> list[dict]:
    """Call the LLM to generate slide content for *topic*.

    Returns a list of dicts with keys:
        - title  (str)
        - bullets (list[str])
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is not set. "
            "Export it before running PptAgente: export OPENAI_API_KEY='sk-...'"
        )
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a presentation expert. "
        "When given a topic, you return a JSON array of slide objects. "
        "Each slide object must have exactly two keys: "
        '"title" (string) and "bullets" (array of strings, 3-5 items). '
        "Return only the raw JSON array with no extra text or markdown."
    )

    user_prompt = (
        f"Create a {num_slides}-slide presentation about: {topic}. "
        "The first slide should be a title/intro slide and the last slide a summary/conclusion."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    raw = response.choices[0].message.content.strip()
    try:
        slides = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"The LLM returned invalid JSON. Response was:\n{raw}"
        ) from exc

    if not isinstance(slides, list):
        raise ValueError(
            f"Expected a JSON array of slides, got: {type(slides).__name__}"
        )
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict) or "title" not in slide or "bullets" not in slide:
            raise ValueError(
                f"Slide {i} is missing required keys 'title' and/or 'bullets': {slide}"
            )
    return slides
