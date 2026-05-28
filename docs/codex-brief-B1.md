Codex-brief: Kipinä Vibe — B1. Prototype API + Mestarin system instructions
Tausta: Kipinä-pilotissa on toimiva päästä päähän -putki ideakeskustelusta konseptiin. Nyt rakennetaan putken viimeinen lenkki: vibekoodausvaihe, jossa "Mestari" muuttaa konseptin selainprototyypiksi. Tämä on B1, ensimmäinen vaihe kolmesta backend-vaiheesta.
Scope: Tässä vaiheessa rakennetaan Prototype API -palvelu joka kutsuu Vertex AI Agent Engineä. STT Proxy (B3) ja Template Proxy (B2) tulevat myöhemmin omissa briefeissään. Älä rakenna niitä nyt.
GCP-resurssit hoidetaan erikseen: Service Account, IAM-roolit ja Agent Engine -instanssi luodaan GCP Consolen kautta. Codexin tehtävä on rakentaa kontaineri ja koodi, joka käyttää näitä env-muuttujien kautta.

1. Tiedostot jotka luodaan
apps/prototype-api/
├── app.py              # HTTP-palvelin (ThreadingHTTPServer)
├── mestari.py          # System instructions, prompt-rakentaminen
├── agent_engine.py     # Vertex AI Agent Engine SDK -kääre
├── sandbox_state.py    # sandbox_id ↔ session_id + html_history in-memory
├── Dockerfile
└── requirements.txt
Muutokset olemassa oleviin tiedostoihin:

docker-compose.yml (uusi service prototype-api)
infra/caddy/Caddyfile (uusi route /api/prototype/*)
.env.example (uudet env-muuttujat)
.gitignore (varmista että secrets/gcp-sa-vibe.json on ignored)

Ei muutoksia: reveal-data-api, concept-api, frontend.

2. requirements.txt
google-cloud-aiplatform>=1.112.0
google-genai>=1.0.0
Käytä google-cloud-aiplatform Agent Engine -sandboxien luontiin ja google-genai Gemini-malliin. Jos jompikumpi versio ei ole saatavilla buildin aikana, pinnaa uusimpaan stable 1.x:ään ja raportoi versiot.

3. Dockerfile
dockerfileFROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mestari.py agent_engine.py sandbox_state.py .

EXPOSE 8080

CMD ["python", "-u", "app.py"]

4. app.py — HTTP-palvelin
Pure stdlib http.server.BaseHTTPRequestHandler + ThreadingHTTPServer. Sama tyyli kuin concept-api/app.py:ssä. Ei Flaskia, ei FastAPIa.
Kuuntelee: 0.0.0.0:8080 kontainerin sisällä, mapattu 127.0.0.1:8083 hostille.
Env-muuttujat:

GCP_PROJECT_ID (esim. apply-project-35406)
GCP_LOCATION (oletus us-central1 — Agent Engine vaatii)
GEMINI_MODEL (oletus gemini-3-pro)
AGENT_ENGINE_ID (täysi resource name: projects/{project}/locations/{location}/reasoningEngines/{id})
GOOGLE_APPLICATION_CREDENTIALS (polku container-mountattuun SA-avaimeen, esim. /secrets/gcp-sa-vibe.json)

CORS: Vastaa OPTIONS-preflighteihin headerilla Access-Control-Allow-Origin: https://pilot.kipina.digiter.fi, allowed methods POST, DELETE, OPTIONS, allowed headers Content-Type.
Lokitus stdoutiin: aikaleima, metodi, polku, status, latenssi ms, sandbox_id jos saatavilla. Yksi rivi per request. Ei lokita request bodyä, prototyyppi-HTML:ää, Mestarin viestiä, konseptia tai raporttia.
4.1 Endpointit
GET /api/prototype/health
200 OK:
json{"ok": true, "service": "kipina-prototype-api"}
POST /api/prototype/start
Request body:
json{
  "concept": "string",
  "report": "string",
  "tenant_id": "string",
  "session_id": "string"
}
Validointi:

concept ja report pakollisia, max 50 000 merkkiä kumpikin
Ei-tyhjiä stringejä
Virheissä: 400 JSON {"error": "...", "detail": "..."}

Toiminta:

Luo uusi Code Execution -sandbox (agent_engine.create_sandbox() luvussa 5)
Tallenna sandbox_id → {session_id, created_at, iteration_count: 0, html_history: []} muistiin (sandbox_state.py)
Kutsu Mestaria luomaan ensimmäinen prototyyppi konseptin pohjalta (mestari.create_initial_prototype() luvussa 6)
Tallenna ensimmäinen HTML html_history-listan ensimmäiseksi
Palauta sandbox_id, HTML ja Mestarin viesti

Response 200:
json{
  "sandbox_id": "string",
  "prototype_html": "string — yksitiedostoinen HTML iframen srcdoc:lle",
  "mestari_message": "string",
  "ttl_seconds": 3600
}
Errors: 400 (validointi), 502 (Vertex AI -virhe), 503 (sandbox-kiintiö täynnä).
POST /api/prototype/iterate
Request:
json{
  "sandbox_id": "string",
  "mode": "koodaus" | "pohdinta",
  "user_input": "string",
  "language": "fi" | "en"
}
Validointi:

sandbox_id löytyy muistista, muuten 404 {"error": "sandbox_not_found"}
mode on "koodaus" tai "pohdinta"
user_input ei-tyhjä, max 5000 merkkiä

Toiminta — Koodaus-tila:

Hae sandbox-tila (html_history, iteration_count, konsepti, raportti — säilytetään sandbox-staten yhteydessä)
Kutsu Mestaria (mestari.iterate_koodaus() luvussa 6) parametreilla: nykyinen HTML, viimeisimmät iteraatiot (max 5), uusi pyyntö
Lisää uusi HTML html_history-listaan, rajoita lista 20 viimeisimpään (FIFO)
Inkrementoi iteration_count
Palauta uusi HTML + Mestarin kommentti + iteration_count

Toiminta — Pohdinta-tila:

Sama kuin Koodaus, mutta kutsu mestari.iterate_pohdinta()
Älä päivitä html_historya (HTML ei muutu)
Palauta pelkkä Mestarin tekstivastaus

Response 200 (Koodaus):
json{
  "prototype_html": "string",
  "mestari_message": "string",
  "iteration_count": 5,
  "concept_drift_warning": null | "string"
}
Response 200 (Pohdinta):
json{
  "mestari_message": "string",
  "iteration_count": 5
}
POST /api/prototype/undo
Request:
json{"sandbox_id": "string"}
Toiminta:

Validoi sandbox elossa
Jos html_history-listassa on vähintään 2 versiota → poppaa viimeisin, palauta toiseksi viimeisin
Jos vain yksi versio → 400 {"error": "no_undo_available", "message": "Tämä on ensimmäinen versio, ei voi peruuttaa."}
Inkrementoi iteration_count, lisää Mestarin kontekstiin tieto undosta seuraavalle iteraatiolle

Response 200:
json{
  "prototype_html": "string",
  "mestari_message": "Palautin edellisen.",
  "iteration_count": 6,
  "undo_available": true
}
DELETE /api/prototype/{sandbox_id}
Päättää session aktiivisesti. Poista sandbox (agent_engine.delete_sandbox(sandbox_id)), poista sandbox_state-merkintä muistista, palauta 204 No Content.

5. agent_engine.py — Vertex AI Agent Engine SDK -kääre
Käytä google-cloud-aiplatform SDK:ta. Esimerkki API:n käytöstä:
pythonfrom google.cloud import aiplatform
from google.cloud.aiplatform import agent_engines

# Käytä env-muuttujia, älä kovakoodaa
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ["GCP_LOCATION"]
AGENT_ENGINE_ID = os.environ["AGENT_ENGINE_ID"]

aiplatform.init(project=PROJECT_ID, location=LOCATION)

def create_sandbox():
    """Luo uusi Code Execution -sandbox JavaScript-tuella, TTL 3600s."""
    # Käytä Vertex AI Agent Engine Code Execution -API:a
    # Dokumentaatio: https://cloud.google.com/agent-builder/agent-engine/code-execution/quickstart
    # Parametrit:
    #   - code_language: LANGUAGE_JAVASCRIPT
    #   - machine_config: MACHINE_CONFIG_VCPU4_RAM4GIB
    #   - ttl: "3600s"
    # Palauta sandbox_id (resource name tai lyhennetty muoto)
    ...

def execute_code(sandbox_id: str, code: str) -> dict:
    """Aja JavaScript-koodi sandboxissa, palauta stdout/stderr."""
    ...

def delete_sandbox(sandbox_id: str):
    """Poista sandbox vapauttaakseen resurssit."""
    ...
Huomio: Code Execution -API saattaa olla vielä preview-tilassa. Tarkista uusimmat dokumentaatiosivut buildin aikana:

https://cloud.google.com/agent-builder/agent-engine/code-execution/overview
https://cloud.google.com/agent-builder/agent-engine/code-execution/quickstart

Jos varsinainen koodin ajaminen sandboxissa ei ole välttämätöntä ensimmäiselle versiolle (Mestari voi tuottaa HTML:n suoraan Gemini-vastauksena ilman sandbox-ajoa), aloita kevyemmästä versiosta: pelkkä Gemini-kutsu joka tuottaa HTML:n, ja sandboxia käytetään myöhemmin syvempään koodin validointiin. Raportoi valinta selvästi koodissa kommenttina ja README:ssä.
Tärkeää: Käytä us-central1-aluetta — Code Execution on tuettu vain siellä.

6. mestari.py — System instructions ja prompt-rakentaminen
Tämä on B1:n tärkein moduuli. Mestari saa persoonansa system instructionsien kautta.
6.1 Kiinteät tekstit
Kaksi monirivistä string-vakiota:
pythonMESTARI_PERUSROOLI = """
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
Huomio Template Librarystä: B1:ssä ei vielä ole Template Proxya, joten Mestarin ohjeissa ei vielä mainita templateja konkreettisesti. B2-vaiheessa lisätään Template Library -kuvaus. Pidä mestari.py:n rakenne sellaisena että B2:n lisäys on helppo (esim. erillinen funktio _build_template_library_section() joka palauttaa pilotin alussa tyhjän stringin).
6.2 Funktiot
pythondef create_initial_prototype(concept: str, report: str, language: str = "fi") -> dict:
    """
    Generoi ensimmäisen prototyypin konseptin pohjalta.
    Palauttaa: {"prototype_html": str, "mestari_message": str}
    """
    ...

def iterate_koodaus(
    current_html: str,
    recent_iterations: list[dict],  # [{user: str, mestari: str}, ...]
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi"
) -> dict:
    """
    Koodaus-tilan iteraatio.
    Palauttaa: {"prototype_html": str, "mestari_message": str, "concept_drift_warning": str|None}
    """
    ...

def iterate_pohdinta(
    current_html: str,
    recent_iterations: list[dict],
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi"
) -> dict:
    """
    Pohdinta-tilan iteraatio.
    Palauttaa: {"mestari_message": str}
    """
    ...
6.3 Strukturoitu output
Käytä Gemini API:n response schema -ominaisuutta (response_mime_type="application/json" + response_schema) jotta Mestarin output on aina parsittavissa. Skeema:
Koodaus-mode:
json{
  "type": "object",
  "properties": {
    "prototype_html": {"type": "string"},
    "mestari_message": {"type": "string"},
    "concept_drift_warning": {"type": "string", "nullable": true}
  },
  "required": ["prototype_html", "mestari_message"]
}
Pohdinta-mode:
json{
  "type": "object",
  "properties": {
    "mestari_message": {"type": "string"}
  },
  "required": ["mestari_message"]
}

7. sandbox_state.py — Muisti
Yksinkertainen thread-safe Python-dictionary:
pythonimport threading
from typing import Optional

_state = {}
_lock = threading.Lock()

def create_session(sandbox_id: str, session_id: str, concept: str, report: str):
    with _lock:
        _state[sandbox_id] = {
            "session_id": session_id,
            "concept": concept,
            "report": report,
            "created_at": time.time(),
            "iteration_count": 0,
            "html_history": [],
            "recent_iterations": [],  # max 5
            "concept_drift_warned": False
        }

def get_session(sandbox_id: str) -> Optional[dict]:
    with _lock:
        return _state.get(sandbox_id)

def add_html_version(sandbox_id: str, html: str):
    """Lisää uusi HTML historiaan, rajoita lista 20:een."""
    ...

def pop_last_html_version(sandbox_id: str) -> Optional[str]:
    """Poppaa viimeisin, palauta toiseksi viimeisin. None jos vain yksi."""
    ...

def add_iteration(sandbox_id: str, user: str, mestari: str):
    """Lisää keskusteluvuoro, rajoita lista 5:een."""
    ...

def mark_drift_warned(sandbox_id: str):
    """Merkitse että drift-varoitus on annettu (max kerran per sessio)."""
    ...

def delete_session(sandbox_id: str):
    with _lock:
        _state.pop(sandbox_id, None)

8. docker-compose.yml -lisäys
Olemassa olevien kipina-hello, kipina-reveal-data-api, kipina-concept-api blockien jälkeen:
yaml  prototype-api:
    build:
      context: ./apps/prototype-api
    container_name: kipina-prototype-api
    restart: unless-stopped
    ports:
      - "127.0.0.1:8083:8080"
    environment:
      GCP_PROJECT_ID: "apply-project-35406"
      GCP_LOCATION: "us-central1"
      GEMINI_MODEL: "gemini-3-pro"
      AGENT_ENGINE_ID: "${AGENT_ENGINE_ID}"
      GOOGLE_APPLICATION_CREDENTIALS: "/secrets/gcp-sa-vibe.json"
    volumes:
      - ./secrets/gcp-sa-vibe.json:/secrets/gcp-sa-vibe.json:ro
AGENT_ENGINE_ID luetaan .env-tiedostosta jotta sitä ei kovakoodata composeen. Lisää .env.example-tiedostoon:
# Vibe Prototype API
AGENT_ENGINE_ID=projects/apply-project-35406/locations/us-central1/reasoningEngines/PLACEHOLDER

9. infra/caddy/Caddyfile -muutos
Lisää ennen olemassa olevaa /api/concepts/*-routea:
pilot.kipina.digiter.fi {
    handle /api/prototype/* {
        reverse_proxy localhost:8083
    }
    handle /api/concepts/* {
        reverse_proxy localhost:8082
    }
    handle /api/* {
        reverse_proxy localhost:8081
    }
    handle {
        reverse_proxy localhost:8080
    }
}
Reload Caddy:
bashsudo systemctl reload caddy
sudo systemctl status caddy

10. GCP-resurssit (Tomi hoitaa Gemini-avusteisena, EI Codexin tehtävä)
Codex ei tee näitä, mutta ne pitää olla valmiina ennen kuin palvelua voi testata:

Service Account kipina-vibe@apply-project-35406.iam.gserviceaccount.com
IAM-roolit: roles/aiplatform.user
JSON-avain ladattuna palvelimelle: /opt/kipina-pilot/secrets/gcp-sa-vibe.json (chmod 600)
Vertex AI Agent Engine -instanssi luotuna us-central1-alueelle
Agent Engine -instanssin resource name kopioitu .env-tiedostoon AGENT_ENGINE_ID-muuttujaan

Jos jokin näistä puuttuu kun Codex käynnistää palvelun, palvelun pitää käynnistyä silti, mutta endpointit palauttavat 503 ja loki kertoo selvästi mikä env-muuttuja tai resurssi puuttuu.

11. Acceptance criteria
Codex on valmis kun KAIKKI alla olevat ovat tosia:

docker compose build prototype-api rakentaa ilman virheitä
docker compose up -d käynnistää palvelun, docker ps näyttää kipina-prototype-api healthy
curl http://localhost:8083/api/prototype/health palauttaa {"ok": true, "service": "kipina-prototype-api"}
curl https://pilot.kipina.digiter.fi/api/prototype/health palauttaa saman (Caddy reitittää)
curl https://pilot.kipina.digiter.fi/api/concepts/health palauttaa edelleen Concept API:n vastauksen (ei rikottu)
curl https://pilot.kipina.digiter.fi/api/health palauttaa edelleen Reveal-proxyn vastauksen
POST /api/prototype/start dummy-konseptilla ja -raportilla palauttaa toimivan yksitiedostoisen HTML:n joka sisältää Tailwind CDN -tagin
Palautettu HTML toimii kun se avataan suoraan selaimessa (kopioi-liitä srcdoc-attribuuttiin)
POST /api/prototype/iterate mode=koodaus muokkaa HTML:n
POST /api/prototype/iterate mode=pohdinta palauttaa pelkän tekstin
POST /api/prototype/undo palauttaa edellisen HTML-version
Kaksi peräkkäistä undoa palauttaa 2 askelta taaksepäin
Undo ensimmäisestä versiosta palauttaa 400 no_undo_available
DELETE /api/prototype/{sandbox_id} palauttaa 204
Mestarin viestit eivät ala kohteliaisuusfraaseilla ("Kiitos", "Hieno", "Ymmärrän") — testaa muutamalla iteraatiolla
Mestarin tuottama HTML ei sisällä henkilötietoja vaikka pyyntö niitä ehdottaisi ("tee Tomin sovellus" → "käyttäjän sovellus")
secrets/gcp-sa-vibe.json on gitignored, mounted read-only
docker logs kipina-prototype-api näyttää yhden lokirivin per request, ei sisällä konsepti- tai HTML-sisältöä


12. Mitä lipata Tomille ennen kuin edetään
Pyydä tarkennusta ennen valmistumista jos:

Vertex AI Agent Engine Code Execution -API on toisenlainen kuin dokumentaation perusteella odotettiin
gemini-3-pro -mallinimi ei ole oikea Vertex AI:n nykyversiossa (raportoi käytetty malli)
IAM-roolit eivät riitä (esim. Agent Engine -sandbox vaatii erillisen roolin)
Sandbox-suoritus on välttämätöntä vai voiko Mestari tuottaa HTML:n suoraan Gemini-vastauksena (ks. luku 5:n huomio)
HTML-validointi: pitääkö palvelun tarkistaa että Mestarin palauttama HTML on validi vai luotetaanko Geminin response schemaan


13. Mitä EI tehdä B1:ssä (myöhemmissä vaiheissa)

Template API Proxy → B2
STT Proxy → B3
Frontend-integraatio → C1
Rate limiting → ei pilotissa
Lokien lähetys johonkin → ei pilotissa, pelkkä stdout riittää
Iteraatiohistorian tiivistys → voidaan lisätä myöhemmin jos pilotti osoittaa tarvetta


Viittaukset:

B-dokumentti: kipina-vibe-B-backend.md (luvut 2, 5, 6, 7)
A-dokumentti: kipina-vibe-A-konsepti.md (Mestari-rooli luku 2)
Esimerkki vastaavasta palvelusta: apps/concept-api/


Brief loppuu. Aloita lukemalla apps/concept-api/ -kansion sisältö koodityyliksi referenssiksi. Jos jokin yllä on epäselvää, pyydä tarkennusta sen sijaan että arvaat.