from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from google import genai


GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
GEMINI_TIMEOUT_SECONDS = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
PORT = int(os.environ.get("PORT", "8080"))

CORS_ORIGIN = "https://pilot.kipina.digiter.fi"
MAX_BODY_BYTES = 128 * 1024
MAX_REPORT_CHARS = 50_000

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
_client: genai.Client | None = None


def log(message: str) -> None:
    print(message, file=sys.stdout, flush=True)


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION,
        )
    return _client


def build_prompt(report: str, language: str) -> str:
    if language == "en":
        return f"""You are a concept designer in the Kipina pilot. You receive a report describing a young person's idea. Your job is to turn it into a concept description that the young person can use to build a working application on a vibe-coding platform (such as Replit, Lovable, or Bolt) in one or a few sessions.

IMPORTANT BUILD CONTEXT:
- The application will be built on a vibe-coding platform that produces browser-based web code (HTML, JavaScript, React).
- The end result is a web app that runs in a browser. No native mobile, no desktop apps.
- The app should be reachable to a working state quickly — favour feasibility over ambition.
- DO NOT propose: custom game engines, 3D graphics, complex editors, drag-and-drop builders, real-time multiplayer, deep native sensor integrations.
- DO NOT propose payment processing or handling of sensitive personal data in any form.
- Vibe-coding platforms are good at: forms, lists, cards, maps, chat views, calendars, filters, search, simple visualisations, API calls, text-based AI interaction.

Prefer "one screen that does one thing well" over "a platform that enables everything". The point is for the young person to see their idea actually working soon — not a promise of a vast system.

Write the concept as free-form prose, not JSON, not tables. Use clear subheadings. Keep the whole concept under 500 words.

Include the following sections, in this order, with exactly these headings:

## Idea name
One short, catchy working title.

## In a nutshell
One sentence: what the app does and for whom.

## User journey
About five numbered steps showing how the user moves through the app from start to value.

## Core features
3–5 bullet-listed features. Each must be something buildable as browser-based web functionality.

## Data flows needed
Bullet-list WHAT KIND of information the app would need from external sources to work meaningfully. DO NOT name any specific service, product, or brand (no Google, OpenAI, Maps, Spotify, etc.). Describe only the NATURE of the data — e.g. "real-time public transport timetables", "public weather data", "text translation between languages", "text-based conversation with an AI", "image recognition from a photo". This list helps developers understand which API integrations the vibe-coding template should expose.

## Building it on a vibe-coding platform
In 2–4 sentences: how would this be built in practice as a browser-based web app? Where to start, what is the simplest working version that can be put on screen first, and what can be layered on top? This section keeps the concept grounded.

Design the concept so that it works well on mobile. Mobile use is a strong starting point: the UI, user journey, and features should be naturally usable in a phone browser. This is not an absolute requirement and the concept does not have to be mobile-only, but the phone screen, touch input, and short bursts of use should guide the design.

Here is the report:

---
{report}
---"""

    return f"""Olet konseptisuunnittelija Kipinä-pilotissa. Saat raportin nuoren ideasta. Tehtäväsi on muotoilla siitä konseptikuvaus, jonka pohjalta nuori voi rakentaa toimivan sovelluksen vibekoodausalustalla (kuten Replit, Lovable tai Bolt) yhdessä tai muutamassa istunnossa.

TÄRKEÄ TOTEUTUSKONTEKSTI:
- Sovellus rakennetaan vibekoodausalustalla, joka tuottaa selainpohjaista web-koodia (HTML, JavaScript, React).
- Lopputulos on selaimessa toimiva web-sovellus. Ei natiivimobiilia, ei työpöytäsovellusta.
- Sovellus tulee voida saada toimivaan kuntoon nopeasti — painota toteutettavuutta yli kunnianhimoa.
- ÄLÄ ehdota: omia pelimoottoreita, 3D-grafiikkaa, kompleksisia editoreita, drag-and-drop -rakentajia, reaaliaikaista multiplayeria, natiivien sensorien syviä integraatioita.
- ÄLÄ ehdota maksuliikennettä tai arkaluontoisen henkilödatan käsittelyä missään muodossa.
- Vibekoodausalustat osaavat tehdä: lomakkeita, listoja, kortteja, karttoja, chat-näkymiä, kalentereita, suodattimia, hakuja, yksinkertaisia visualisointeja, API-kutsuja, tekstipohjaista tekoälyvuorovaikutusta.

Mieluummin "yksi näyttö joka tekee yhden asian hyvin" kuin "alusta joka mahdollistaa kaiken". Onnistumisen ydin on että nuori näkee oman ideansa toimivan oikeasti pian — ei lupausta valtavasta järjestelmästä.

Kirjoita konsepti vapaamuotoisena tekstinä, ei JSONina, ei taulukoina. Käytä selkeitä alaotsikoita. Pidä koko konsepti alle 500 sanan mittaisena.

Sisällytä seuraavat osiot, tässä järjestyksessä, tarkalleen näillä otsikoilla:

## Idean nimi
Yksi lyhyt, iskevä työnimi.

## Pähkinänkuoressa
Yksi lause: mitä sovellus tekee ja kenelle.

## Käyttäjäpolku
Noin viisi numeroitua askelta siitä, miten käyttäjä etenee sovelluksessa alusta hyödyn saamiseen.

## Ydintoiminnot
3–5 ranskalaisella viivalla listattua toiminnallisuutta. Jokaisen tulee olla sellainen, jonka voi rakentaa selainpohjaisena web-toiminnallisuutena.

## Tarvittavat tietovirrat
Listaa ranskalaisilla viivoilla, MILLAISTA tietoa sovellus tarvitsisi ulkoisista lähteistä toimiakseen järkevästi. ÄLÄ nimeä mitään konkreettista palvelua, tuotetta tai brändiä (älä mainitse Googlea, OpenAI:ta, Mapsia, Spotifyta tms.). Kuvaa vain tiedon LUONNE — esimerkiksi: "reaaliaikaista joukkoliikenteen aikataulutietoa", "julkista säätietoa", "tekstin kääntämistä kielestä toiseen", "tekstipohjaista keskustelua tekoälyn kanssa", "kuvantunnistusta valokuvasta". Tämä lista auttaa kehittäjiä ymmärtämään, mitä API-rajapintoja vibekoodausalustan templaten tulisi tarjota.

## Toteutus vibekoodausalustalla
2–4 lauseessa: miten tämä rakennetaan käytännössä selainpohjaisena web-sovelluksena? Mistä aloittaa, mikä on yksinkertaisin toimiva versio jonka voi saada näytölle ensimmäisenä, ja mitä päälle voi laajentaa? Tämä osio pitää konseptin maan pinnalla.

Suunnittele konsepti niin, että se toimii hyvin mobiililla. Mobiilikäyttö on vahva lähtökohta: käyttöliittymä, käyttäjäpolku ja toiminnot tulee voida toteuttaa luontevasti puhelimen selaimessa. Tämä ei ole ehdoton vaatimus, eikä konseptin tarvitse olla vain mobiililla toimiva, mutta puhelimen ruutu, kosketuskäyttö ja lyhyet käyttöhetket ohjaavat suunnittelua.

Tässä on raportti:

---
{report}
---"""


def generate_concept(prompt: str) -> str:
    client = get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _log_request(self, status: int, elapsed_ms: float) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path = urlparse(self.path).path
        log(f"{timestamp} {self.command} {path} {status} {elapsed_ms:.1f}ms")

    def _send_json(self, status: int, payload: dict[str, Any]) -> int:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.end_headers()
        self.wfile.write(body)
        return status

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return data

    def _send_cors_preflight(self) -> int:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return 204

    def do_OPTIONS(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        try:
            status = self._send_cors_preflight()
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000)

    def do_GET(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        try:
            path = urlparse(self.path).path
            if path == "/api/concepts/health":
                status = self._send_json(
                    200,
                    {"ok": True, "service": "kipina-concept-api"},
                )
            else:
                status = self._send_json(404, {"error": "not_found"})
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000)

    def do_POST(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        try:
            path = urlparse(self.path).path
            if path != "/api/concepts/generate":
                status = self._send_json(404, {"error": "not_found"})
                return
            status = self._handle_generate()
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000)

    def _handle_generate(self) -> int:
        body = self._read_json_body()
        if body is None:
            return self._send_json(400, {"error": "report is required"})

        report = body.get("report")
        if not isinstance(report, str) or not report.strip():
            return self._send_json(400, {"error": "report is required"})
        if len(report) > MAX_REPORT_CHARS:
            return self._send_json(400, {"error": "report too long"})

        language = body.get("language", "fi")
        if language != "en":
            language = "fi"

        prompt = build_prompt(report.strip(), language)
        future = _executor.submit(generate_concept, prompt)
        try:
            concept_text = future.result(timeout=GEMINI_TIMEOUT_SECONDS)
        except Exception as exc:
            if isinstance(exc, concurrent.futures.TimeoutError):
                detail = f"Gemini request timed out after {GEMINI_TIMEOUT_SECONDS}s"
            else:
                detail = str(exc)[:240] or exc.__class__.__name__
            log("Gemini concept generation failed:")
            traceback.print_exc(file=sys.stdout)
            return self._send_json(
                502,
                {"error": "concept generation failed", "detail": detail},
            )

        return self._send_json(200, {"concept": concept_text})


def main() -> None:
    if not GCP_PROJECT_ID:
        log("WARNING: GCP_PROJECT_ID is not set.")
    if not GOOGLE_APPLICATION_CREDENTIALS:
        log("WARNING: GOOGLE_APPLICATION_CREDENTIALS is not set.")
    log(
        "kipina-concept-api starting "
        f"model={GEMINI_MODEL} project={GCP_PROJECT_ID or '-'} location={GCP_LOCATION}"
    )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log(f"kipina-concept-api listening on 0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutting down")
    finally:
        server.server_close()
        _executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
