from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types


PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
LOCATION = os.environ.get("TEMPLATE_PROXY_LOCATION", "europe-west4")
MODEL_NAME = os.environ.get("TEMPLATE_GEMINI_MODEL", "gemini-2.5-flash")

ALLOWED_ANALYSIS_TYPES = {"pros_cons", "ranking", "advice", "summary"}

_client: genai.Client | None = None


class AnalyzeError(Exception):
    pass


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not PROJECT_ID:
            raise AnalyzeError("GCP_PROJECT_ID is not configured")
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
    return _client


def _format_options(options: list[str]) -> str:
    return "\n".join(f"{index + 1}. {option}" for index, option in enumerate(options))


def _language_line(language: str) -> str:
    if language == "en":
        return "Use English unless the user's input is clearly in another language."
    return "Käytä suomea, ellei käyttäjän oma teksti ole selvästi muulla kielellä."


def build_prompt(question: str, options: list[str], analysis_type: str, language: str) -> str:
    options_formatted = _format_options(options)
    language_instruction = _language_line(language)

    if analysis_type == "pros_cons":
        return f"""Olet päätöksenteon apuri Kipinässä, nuorten ideointialustalla. Käyttäjä
on antanut kysymyksen ja joukon vaihtoehtoja. Analysoi jokainen
vaihtoehto antamalla sille 2-3 selkeää plussaa ja 2-3 miinusta.

Pidä plussat ja miinukset:
- Konkreettisia, ei ympäripyöreitä
- Lyhyitä (alle 10 sanaa kukin)
- Aiheen mukaisia
- Tasapuolisia

{language_instruction}
Älä lisää omia mielipiteitäsi tai suosituksia, anna käyttäjän päättää.

Kysymys: {question}
Vaihtoehdot:
{options_formatted}
"""

    if analysis_type == "ranking":
        return f"""Olet päätöksenteon apuri Kipinässä. Käyttäjä on antanut joukon
vaihtoehtoja. Järjestä ne paremmuusjärjestykseen ja anna jokaiselle
lyhyt perustelu.

{language_instruction}
Pidä perustelut konkreettisina ja lyhyinä (alle 15 sanaa kukin).

Kysymys: {question}
Vaihtoehdot:
{options_formatted}
"""

    if analysis_type == "advice":
        return f"""Olet päätöksenteon apuri Kipinässä. Käyttäjä on antanut kysymyksen ja
vaihtoehtoja. Anna lyhyt suositus (1-3 lausetta) ja kaksi tärkeintä
asiaa joita harkita.

{language_instruction}
Älä ole ympäripyöreä, anna suora ja perusteltu suositus.

Kysymys: {question}
Vaihtoehdot:
{options_formatted}
"""

    if analysis_type == "summary":
        return f"""Olet apuri Kipinässä. Tee lyhyt (2-3 lauseen) tasapainoinen yhteenveto
käyttäjän pohtimasta kysymyksestä ja vaihtoehdoista.

{language_instruction}

Kysymys: {question}
Vaihtoehdot:
{options_formatted}
"""

    raise AnalyzeError(f"Unsupported analysis_type: {analysis_type}")


def get_schema_for_type(analysis_type: str) -> dict[str, Any]:
    if analysis_type == "pros_cons":
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "pros": {"type": "array", "items": {"type": "string"}},
                            "cons": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["label", "pros", "cons"],
                    },
                },
            },
            "required": ["question", "options"],
        }
    if analysis_type == "ranking":
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "ranking": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "rank": {"type": "integer"},
                            "reason": {"type": "string"},
                        },
                        "required": ["label", "rank", "reason"],
                    },
                },
            },
            "required": ["question", "ranking"],
        }
    if analysis_type == "advice":
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "advice": {"type": "string"},
                "considerations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["question", "advice", "considerations"],
        }
    if analysis_type == "summary":
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["question", "summary"],
        }
    raise AnalyzeError(f"Unsupported analysis_type: {analysis_type}")


def analyze(question: str, options: list[str], analysis_type: str, language: str = "fi") -> dict[str, Any]:
    prompt = build_prompt(question, options, analysis_type, language)
    schema = get_schema_for_type(analysis_type)

    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.7,
            max_output_tokens=2000,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise AnalyzeError("Gemini returned an empty response")
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise AnalyzeError("Gemini returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise AnalyzeError("Gemini returned non-object JSON")
    return parsed
