from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types


GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro")
MAX_HTML_CHARS = 50_000

_client: genai.Client | None = None


MESTARI_PERUSROOLI = """
Olet Mestari Kipinässä. Tehtäväsi on rakentaa nuoren idea näkyväksi
selainprototyyppinä, käsityöläisen tarkkuudella ja lämmöllä.

Olet käsityöläinen, et opettaja, et terapeutti, et mentori. Et yritä
kasvattaa nuorta. Teet hänen ideastaan näkyvän ja toimivan, niin että
hän näkee ja tuntee sen.

Puhut nuorelle lämpimästi mutta lyhyesti. Et imartele, et kiitä
jokaisesta vuorosta, et selitä tekemistäsi pitkästi. Mieluummin
"vaihdetaan väri vihreäksi ja katsotaan miltä näyttää" kuin
"Hieno valinta! Vihreä on rauhoittava väri...".

Et aloita vuoroja kohteliaisuusfraaseilla. Et toista samoja
fraaseja vuorosta toiseen.
"""

MESTARI_TEHTAVAKUVA = """
Sinulla on kaksi tilaa:

KOODAUS-TILA: Käyttäjän pyyntö tulkitaan muutoksena prototyyppiin.
Teet muutoksen ja palautat uuden yksitiedostoisen HTML:n. Lisäät
mukaan lyhyen kommentin (1-2 lausetta).

POHDINTA-TILA: Käyttäjän pyyntö on keskustelua, ei muutospyyntö.
Vastaat tekstinä, et muuta koodia. Voit jutella suunnasta,
vaihtoehdoista, perustella aiempia päätöksiä.

Tilan ratkaisee aina käyttäjän järjestelmäkonteksti, ei sinun
päätöksesi. Älä koskaan koodaa Pohdinta-tilassa tai vastaa pelkällä
tekstillä Koodaus-tilassa.

PROTOTYYPIN OUTPUT-FORMAATTI:

- Tuotat aina yksitiedostoisen HTML:n joka toimii iframe srcdoc:issa
- Käytät joko: (a) puhdas HTML + CSS + vanilla JS, tai (b) React +
  Babel standalone CDN:istä jos UI vaatii sitä
- Et koskaan käytä npm-paketteja, build-vaihetta tai ulkoisia
  riippuvuuksia paitsi Template Libraryn endpointit (myöhemmin)
- Käytät Tailwind CSS:ää tyylittelyyn CDN:istä:
  <script src="https://cdn.tailwindcss.com"></script>
- HTML:n max-koko: 50 000 merkkiä

KONSEPTIUSKOLLISUUS:

- Et keksi nuoren puolesta. Kaikki muutokset perustuvat hänen
  pyyntöönsä tai alkuperäiseen konseptiin
- Jos nuori pyytää muutoksen joka vie kauas konseptista, voit
  kerran istunnon aikana muistuttaa: "Pidetäänkö kiinni
  alkuperäisestä ideasta?"
- Jos nuori vahvistaa, että hän haluaa vaihtaa suuntaa, seuraat
  hänen päätöstään

HENKILÖTIEDOT:

- Et pyydä etkä käytä nuoren henkilötietoja prototyypissä
- Jos nuori antaa nimensä tai muun henkilötiedon, käytät yleistä
  ilmaisua ("käyttäjän sovellus")
- Et koskaan tallenna henkilötietoja prototyypin koodiin
"""


CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "prototype_html": {"type": "string"},
        "mestari_message": {"type": "string"},
        "concept_drift_warning": {"type": "string", "nullable": True},
    },
    "required": ["prototype_html", "mestari_message"],
}

TEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "mestari_message": {"type": "string"},
    },
    "required": ["mestari_message"],
}


class MestariError(Exception):
    pass


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GCP_PROJECT_ID:
            raise MestariError("GCP_PROJECT_ID is not configured")
        _client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION,
        )
    return _client


def _build_template_library_section() -> str:
    return ""


def _system_instruction() -> str:
    return "\n\n".join(
        part
        for part in [
            MESTARI_PERUSROOLI.strip(),
            MESTARI_TEHTAVAKUVA.strip(),
            _build_template_library_section().strip(),
        ]
        if part
    )


def _language_instruction(language: str) -> str:
    if language == "en":
        return "Write mestari_message in English. Keep the prototype UI language consistent with the concept unless the user asks otherwise."
    return "Kirjoita mestari_message suomeksi. Pidä prototyypin käyttöliittymä konseptin kielellä, ellei käyttäjä pyydä muuta."


def _generate_json(prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_system_instruction(),
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise MestariError("Gemini returned an empty response")
    try:
        return json.loads(text)
    except ValueError as exc:
        raise MestariError("Gemini returned invalid JSON") from exc


def _validate_html(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MestariError("prototype_html missing from Mestari response")
    html = value.strip()
    if len(html) > MAX_HTML_CHARS:
        raise MestariError("prototype_html exceeded 50000 characters")
    if "https://cdn.tailwindcss.com" not in html:
        raise MestariError("prototype_html missing Tailwind CDN tag")
    return html


def _message(value: Any, fallback: str = "Muutin prototyyppiä.") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _format_recent_iterations(recent_iterations: list[dict]) -> str:
    if not recent_iterations:
        return "Ei aiempia iteraatioita."
    lines = []
    for item in recent_iterations[-5:]:
        user = str(item.get("user", "")).strip()
        mestari = str(item.get("mestari", "")).strip()
        lines.append(f"- Käyttäjä: {user}\n  Mestari: {mestari}")
    return "\n".join(lines)


def create_initial_prototype(concept: str, report: str, language: str = "fi") -> dict:
    prompt = f"""
TILA: KOODAUS

Tehtävä: Luo ensimmäinen selainprototyyppi konseptin pohjalta.

{_language_instruction(language)}

Rakenna yksi ehjä HTML-dokumentti. Sen pitää sisältää:
- <!doctype html>, html, head ja body
- Tailwind CDN -script tagi
- mobiilissa toimiva responsiivinen käyttöliittymä
- vähän demo-dataa vain silloin kun se tekee prototyypin ymmärrettäväksi
- ei henkilötietoja, ei oikeita nimiä, ei ulkopuolisia tunnisteita

Pidä prototyyppi konkreettisena: käyttäjän pitää nähdä heti mitä sovellus tekee.
Palauta vain JSON skeeman mukaisesti.

KONSEPTI:
---
{concept}
---

RAPORTTI:
---
{report}
---
"""
    data = _generate_json(prompt, CODE_SCHEMA)
    return {
        "prototype_html": _validate_html(data.get("prototype_html")),
        "mestari_message": _message(data.get("mestari_message"), "Rakensin ensimmäisen version."),
        "concept_drift_warning": data.get("concept_drift_warning"),
    }


def iterate_koodaus(
    current_html: str,
    recent_iterations: list[dict],
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi",
) -> dict:
    prompt = f"""
TILA: KOODAUS

Tehtävä: Muuta prototyyppiä käyttäjän uuden pyynnön mukaan.

{_language_instruction(language)}

Säännöt:
- Palauta kokonainen uusi HTML-dokumentti, ei diffiä.
- Säilytä toimivat osat ellei käyttäjä pyydä muuttamaan niitä.
- Jos käyttäjä antaa henkilötietoja, yleistät ne prototyypissä.
- Jos pyyntö vie selvästi kauas konseptista, täytä concept_drift_warning lyhyellä muistutuksella. Muuten null.

KÄYTTÄJÄN UUSI PYYNTÖ:
---
{user_input}
---

NYKYINEN HTML:
---
{current_html}
---

VIIMEISIMMÄT ITERAATIOT:
{_format_recent_iterations(recent_iterations)}

ALKUPERÄINEN KONSEPTI:
---
{concept}
---

ALKUPERÄINEN RAPORTTI:
---
{report}
---
"""
    data = _generate_json(prompt, CODE_SCHEMA)
    warning = data.get("concept_drift_warning")
    if not isinstance(warning, str) or not warning.strip():
        warning = None
    return {
        "prototype_html": _validate_html(data.get("prototype_html")),
        "mestari_message": _message(data.get("mestari_message")),
        "concept_drift_warning": warning,
    }


def iterate_pohdinta(
    current_html: str,
    recent_iterations: list[dict],
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi",
) -> dict:
    prompt = f"""
TILA: POHDINTA

Tehtävä: Vastaa käyttäjälle tekstinä. Älä muuta HTML:ää.

{_language_instruction(language)}

Vastaa lyhyesti ja käytännöllisesti. Voit ehdottaa 1-3 vaihtoehtoa, mutta älä
tuota koodia, HTML:ää tai muutettua prototyyppiä.

KÄYTTÄJÄN VIESTI:
---
{user_input}
---

NYKYINEN HTML KONTEKSTINA:
---
{current_html}
---

VIIMEISIMMÄT ITERAATIOT:
{_format_recent_iterations(recent_iterations)}

ALKUPERÄINEN KONSEPTI:
---
{concept}
---

ALKUPERÄINEN RAPORTTI:
---
{report}
---
"""
    data = _generate_json(prompt, TEXT_SCHEMA)
    return {"mestari_message": _message(data.get("mestari_message"), "Voidaan miettiä suuntaa ennen muutosta.")}
