# Codex-brief: Kipinä Vibe — B2a. Template Proxy + Analyze-endpoint

**Tausta:** Kipinä Vibe -putki toimii nyt päästä päähän: Reveal-keskustelu → konsepti → Mestarin vibekoodaus → toimiva selainprototyyppi. Mestari osaa tehdä interaktiivisia sovelluksia, mutta sovelluksen sisäinen "äly" puuttuu — esimerkiksi päätöspäiväkirjasovellus kerää käyttäjän valintoja mutta ei voi analysoida niitä, koska prototyypin sisällä ei voi kutsua LLM:ää suoraan (API-avain ei saa vuotaa selaimeen).

B2a rakentaa ensimmäisen Template Library -endpointin: **`POST /api/templates/analyze`**. Mestarin generoima prototyyppi voi kutsua tätä endpointtia saadakseen Gemini Flash -pohjaista analyysiä, ja API-avain pysyy palvelimella.

**Scope B2a:n osalta:**

Mukana:
- Uusi palvelu `apps/template-proxy/` portissa 127.0.0.1:8085
- Yksi endpoint: `POST /api/templates/analyze`
- Kevyt rate limiting per sandbox (in-memory, 100 kutsua/h)
- Caddy-reititys `/api/templates/*` → portti 8085
- Mestarin Instructions -lisäys joka kuvaa analyze-templaten käytön

**EI mukana B2a:ssa** (tulee B2b:ssä myöhemmin):
- Loput 12 templatea (sää, joukkoliikenne, kartat, kuvat, jne.)
- Pysyvä rate limiting -tietokanta
- Authentication / autorisaatio (Caddy hoitaa sen pilotissa muiden palveluiden tavoin)

B2a on **tarkoituksellisesti minimaalinen** — yksi endpoint joka kuitenkin avaa Mestarille koko uuden kategorian sovellustyyppejä. Kun se on koeteltu, B2b lisää loput templatet samaan palveluun.

---

## 1. Tiedostot jotka luodaan

```
apps/template-proxy/
├── app.py              # HTTP-palvelin (ThreadingHTTPServer)
├── analyze.py          # Analyze-templaten toteutus + Gemini Flash -kutsu
├── rate_limit.py       # In-memory rate limiting per sandbox
├── Dockerfile
├── requirements.txt
└── README.md
```

Muutokset olemassa oleviin tiedostoihin:
- `docker-compose.yml` (uusi service `template-proxy`)
- `infra/caddy/Caddyfile` (uusi route `/api/templates/*`)
- `.env.example` (uudet env-muuttujat)
- Agent Builderissa Kipina-Mestari -agentin Instructions-kenttä (lisäys joka kuvaa analyze-templaten — tehdään manuaalisesti UI:sta, ei Codexin koodimuutosta)

Ei muutoksia: `reveal-data-api`, `concept-api`, `prototype-api`, frontend.

---

## 2. requirements.txt

```
google-genai>=1.0.0
```

Käytetään pelkkää `google-genai` SDK:ta — analyze-template ei tarvitse Agent Engine -ominaisuuksia, vain suora Gemini Flash -kutsu.

---

## 3. Dockerfile

```dockerfile
FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py analyze.py rate_limit.py .

EXPOSE 8080

CMD ["python", "-u", "app.py"]
```

---

## 4. app.py — HTTP-palvelin

Pure stdlib `http.server.BaseHTTPRequestHandler` + `ThreadingHTTPServer`. Sama tyyli kuin `prototype-api/app.py`:ssä ja `concept-api/app.py`:ssä.

**Kuuntelee:** `0.0.0.0:8080` kontainerin sisällä, mapattu `127.0.0.1:8085` hostille.

**Env-muuttujat:**
- `GCP_PROJECT_ID` (esim. `apply-project-35406`)
- `TEMPLATE_PROXY_LOCATION` (oletus `us-central1` tai `europe-west4` — kumpi tahansa Gemini Flashin tukema, suositellaan samaa kuin Concept API:lla yhtenäisyyden vuoksi)
- `TEMPLATE_GEMINI_MODEL` (oletus `gemini-2.5-flash` — nopeampi ja halvempi kuin Pro, riittää analyysi-templatelle)
- `GOOGLE_APPLICATION_CREDENTIALS` (polku container-mountattuun SA-avaimeen, esim. `/secrets/gcp-sa-vibe.json` — sama SA kuin Prototype API:lla, koska se on jo provisioitu `aiplatform.user`-roolilla)

**CORS:** Vastaa OPTIONS-preflighteihin headerilla `Access-Control-Allow-Origin: https://pilot.kipina.digiter.fi`, allowed methods `POST, OPTIONS`, allowed headers `Content-Type, X-Kipina-Sandbox-Id`. **Tärkeää:** salli myös `null`-origin (eli `Access-Control-Allow-Origin: *` mikäli tämä on yhteensopiva muiden palveluiden kanssa) — koska Mestarin prototyyppi pyörii iframen `srcdoc`-attribuutissa, sen origin voi olla `null`. Jos `*` ei sovi, käytä `Access-Control-Allow-Origin: null` erikseen `Origin: null`-pyynnöille.

**Lokitus stdoutiin:** aikaleima, metodi, polku, status, latenssi ms, sandbox_id jos saatavilla. Yksi rivi per request. **Ei** lokita request bodyä eikä Geminin vastausta — vain rate-limiting-tilannetta ("rate_limited" tai "ok").

### 4.1 Endpointit

#### `GET /api/templates/health`

200 OK:
```json
{"ok": true, "service": "kipina-template-proxy", "templates": ["analyze"]}
```

`templates`-kenttä listaa käytettävissä olevat templatet. B2a:ssa tämä on vain `["analyze"]`, B2b:ssä lisätään loput.

#### `POST /api/templates/analyze`

**Request body:**
```json
{
  "question": "string — käyttäjän pohdittava kysymys tai aihe",
  "options": ["string", "string", ...],
  "analysis_type": "pros_cons" | "ranking" | "advice" | "summary",
  "language": "fi" | "en"
}
```

**Validointi:**
- `question`: pakollinen, ei-tyhjä, max 500 merkkiä
- `options`: pakollinen, 1–10 vaihtoehtoa, jokainen max 500 merkkiä
- `analysis_type`: pakollinen, validit arvot: `pros_cons`, `ranking`, `advice`, `summary`
- `language`: vapaaehtoinen, oletus `fi`
- Header `X-Kipina-Sandbox-Id`: pakollinen rate limitingia varten (Mestari välittää sandbox_id:n iframen koodista — ks. luku 8 alla)

Virheissä: 400 JSON `{"error": "...", "detail": "..."}`

**Toiminta:**
1. Tarkista rate limit (`rate_limit.check(sandbox_id)`). Jos täynnä, 429 Too Many Requests.
2. Lisää sandbox-laskuriin
3. Rakenna prompt analysis_typen mukaan (ks. luku 5)
4. Kutsu Gemini Flash mallia (`gemini-2.5-flash`)
5. Palauta strukturoitu vastaus

**Response 200, analysis_type = "pros_cons":**
```json
{
  "question": "Mitä söisin tänään?",
  "options": [
    {
      "label": "Nakkiperunamuusi",
      "pros": ["Nopea valmistaa", "Käytetään hyödyksi jääkaapin sisältö"],
      "cons": ["Yksitoikkoinen", "Ei kovin kevyt"]
    },
    {
      "label": "Pakastepizza",
      "pros": ["Helppo ja maukas", "30 minuuttia uunissa"],
      "cons": ["Vähän epäterveellinen", "Pidempi odotus kuin lämmittäminen"]
    }
  ]
}
```

**Response 200, analysis_type = "ranking":**
```json
{
  "question": "...",
  "ranking": [
    {"label": "Vaihtoehto B", "rank": 1, "reason": "..."},
    {"label": "Vaihtoehto A", "rank": 2, "reason": "..."}
  ]
}
```

**Response 200, analysis_type = "advice":**
```json
{
  "question": "...",
  "advice": "Suosittelen vaihtoehtoa A koska...",
  "considerations": ["Pohdi myös", "Huomioi"]
}
```

**Response 200, analysis_type = "summary":**
```json
{
  "question": "...",
  "summary": "Yhteenveto vaihtoehdoista lyhyesti."
}
```

**Errors:**
- 400 (validointi)
- 429 (rate limit täynnä, body sisältää `retry_after_seconds`)
- 502 (Gemini-virhe, body sisältää `detail`)

---

## 5. analyze.py — Gemini Flash -kutsu ja prompt

Modul rakentaa promptin analysis_typen mukaan, kutsuu Gemini Flashia ja parsii vastauksen.

### 5.1 Promptit

Neljä erilaista prompttia, jokainen analysis_typelle. Käytä strukturoitua outputtia (`response_schema`) jotta vastaus on aina parsittavissa.

**pros_cons -prompt:**

```
Olet päätöksenteon apuri Kipinässä, nuorten ideointialustalla. Käyttäjä
on antanut kysymyksen ja joukon vaihtoehtoja. Analysoi jokainen
vaihtoehto antamalla sille 2-3 selkeää plussaa ja 2-3 miinusta.

Pidä plussat ja miinukset:
- Konkreettisia, ei ympäripyöreitä
- Lyhyitä (alle 10 sanaa kukin)
- Aiheen mukaisia (ei keksi yleisiä mietteitä joilla ei ole liittymää
  käyttäjän kysymykseen)
- Tasapuolisia (jokaisella vaihtoehdolla on sekä hyviä että huonoja
  puolia)

Käytä käyttäjän omaa kieltä. Jos käyttäjä antoi tekstin suomeksi, vastaa
suomeksi. Älä lisää omia mielipiteitäsi tai suosituksia — anna käyttäjän
päättää.

Kysymys: {question}
Vaihtoehdot: {options_formatted}
```

**ranking -prompt:**

```
Olet päätöksenteon apuri Kipinässä. Käyttäjä on antanut joukon
vaihtoehtoja. Järjestä ne paremmuusjärjestykseen ja anna jokaiselle
lyhyt perustelu.

Käytä käyttäjän omaa kieltä. Pidä perustelut konkreettisina ja lyhyinä
(alle 15 sanaa kukin).

Kysymys: {question}
Vaihtoehdot: {options_formatted}
```

**advice -prompt:**

```
Olet päätöksenteon apuri Kipinässä. Käyttäjä on antanut kysymyksen ja
vaihtoehtoja. Anna lyhyt suositus (1-3 lausetta) ja kaksi tärkeintä
asiaa joita harkita.

Käytä käyttäjän omaa kieltä. Älä ole ympäripyöreä — anna suora ja
perusteltu suositus.

Kysymys: {question}
Vaihtoehdot: {options_formatted}
```

**summary -prompt:**

```
Olet apuri Kipinässä. Tee lyhyt (2-3 lauseen) tasapainoinen yhteenveto
käyttäjän pohtimasta kysymyksestä ja vaihtoehdoista.

Käytä käyttäjän omaa kieltä.

Kysymys: {question}
Vaihtoehdot: {options_formatted}
```

### 5.2 Response schemat

Käytä Gemini API:n `response_mime_type="application/json"` + `response_schema` jotta output on aina valid JSON. Skeemat vastaavat luvun 4.1 Response 200 -muotoja.

### 5.3 Yksinkertainen toteutus

```python
from google import genai

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

def analyze(question, options, analysis_type, language="fi"):
    prompt = build_prompt(question, options, analysis_type, language)
    schema = get_schema_for_type(analysis_type)

    response = client.models.generate_content(
        model=MODEL_NAME,  # "gemini-2.5-flash"
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": schema,
            "temperature": 0.7,  # tasapaino luovuus / kurinalaisuus
            "max_output_tokens": 2000
        }
    )

    return json.loads(response.text)
```

---

## 6. rate_limit.py — In-memory rate limiting

Yksinkertainen thread-safe Python-dictionary joka pitää kirjaa per sandbox_id.

```python
import threading
import time
from collections import deque
from typing import Optional

_counters = {}  # sandbox_id -> deque of timestamps
_lock = threading.Lock()

RATE_LIMIT_PER_HOUR = 100
WINDOW_SECONDS = 3600

def check(sandbox_id: str) -> Optional[int]:
    """
    Tarkista onko sandbox-id:llä vielä kutsuja jäljellä.
    Palauttaa None jos OK, tai retry_after_seconds jos rate limit täynnä.
    """
    now = time.time()
    with _lock:
        if sandbox_id not in _counters:
            _counters[sandbox_id] = deque()
        timestamps = _counters[sandbox_id]
        # Poista vanhentuneet timestampit
        while timestamps and timestamps[0] < now - WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT_PER_HOUR:
            retry_after = int(timestamps[0] + WINDOW_SECONDS - now) + 1
            return retry_after
        timestamps.append(now)
        return None
```

**Huomio:** in-memory rate limiting häviää kun palvelu käynnistyy uudelleen. Tämä on hyväksyttävä pilottirajoitus — emme rakennetaa Redis-pohjaista rate limitingia vielä.

**Huomio 2:** `X-Kipina-Sandbox-Id` -header on käytännössä **vahvistamaton** — Mestarin generoima prototyyppi voi periaatteessa väärentää sen. Tämä on tarkoituksellinen pilotissa, koska:
- Pilotissa käyttäjäjoukko on pieni ja hallittavissa
- Vakavasti väärentämällä saa max 100 lisäkutsua/h, ei rajatonta käyttöä
- Globaali rate limit ehkäisee massakäytön (ks. luku 6.1)

### 6.1 Globaali rate limit

Lisätään yksinkertainen globaali raja yli kaikkien sandbox-ID:iden:

```python
GLOBAL_RATE_LIMIT_PER_DAY = 5000
_global_counter = deque()
_global_lock = threading.Lock()

def check_global() -> Optional[int]:
    now = time.time()
    with _global_lock:
        while _global_counter and _global_counter[0] < now - 86400:
            _global_counter.popleft()
        if len(_global_counter) >= GLOBAL_RATE_LIMIT_PER_DAY:
            return int(_global_counter[0] + 86400 - now) + 1
        _global_counter.append(now)
        return None
```

Endpointissa tarkistetaan ensin globaali raja, sitten sandbox-kohtainen. Jos jompikumpi täynnä, 429.

---

## 7. docker-compose.yml -lisäys

Olemassa olevien `kipina-hello`, `kipina-reveal-data-api`, `kipina-concept-api`, `kipina-prototype-api` -blokkien jälkeen:

```yaml
  template-proxy:
    build:
      context: ./apps/template-proxy
    container_name: kipina-template-proxy
    restart: unless-stopped
    ports:
      - "127.0.0.1:8085:8080"
    environment:
      GCP_PROJECT_ID: "apply-project-35406"
      TEMPLATE_PROXY_LOCATION: "us-central1"
      TEMPLATE_GEMINI_MODEL: "gemini-2.5-flash"
      GOOGLE_APPLICATION_CREDENTIALS: "/secrets/gcp-sa-vibe.json"
    volumes:
      - ./secrets/gcp-sa-vibe.json:/secrets/gcp-sa-vibe.json:ro
```

Lisää `.env.example`-tiedostoon:

```
# Template Proxy (Gemini Flash analyysit)
TEMPLATE_PROXY_LOCATION=us-central1
TEMPLATE_GEMINI_MODEL=gemini-2.5-flash
```

---

## 8. infra/caddy/Caddyfile -muutos

Lisää **ennen** olemassa olevia spesifejä reittejä mutta **jälkeen** muiden `/api/*`-reittien jotka on jo nimetty:

```
pilot.kipina.digiter.fi {
    handle /api/prototype/* {
        reverse_proxy localhost:8083
    }
    handle /api/templates/* {
        reverse_proxy localhost:8085
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
```

Reload Caddy:
```bash
sudo systemctl reload caddy
sudo systemctl status caddy
```

---

## 9. Mestarin Instructions -lisäys (Agent Builder, manuaalinen)

**Tämä ei ole Codexin tehtävä** — Tomi tekee tämän Agent Builderin UI:sta sen jälkeen kun B2a on deployattu ja testattu palvelimella.

Lisää Mestarin Instructions-kenttään seuraava osio aiempien ohjeiden perään:

```
KIPINÄ TEMPLATE LIBRARY — KÄYTETTÄVISSÄ OLEVAT RAJAPINNAT:

Sinulla on käytössäsi yksi palvelinpuolinen rajapinta jonka kautta
prototyyppi voi saada Gemini-pohjaista älyä:

POST /api/templates/analyze
- Header: X-Kipina-Sandbox-Id (käytä prototyypille välitettyä
  sandbox_id-arvoa)
- Body: { question, options, analysis_type, language }
- analysis_type: "pros_cons" | "ranking" | "advice" | "summary"
- Vastaus: strukturoitu JSON analyysityypin mukaan

KÄYTÄ TÄTÄ KUN:
- Sovellus tarvitsee analyysiä käyttäjän syöttämistä vaihtoehdoista
- Sovellus tarvitsee suosituksia tai päätösapua
- Sovellus tarvitsee yhteenvedon tai järjestyksen
- Sovellus tarvitsee älyä mikä ei mahdu kovakoodattuun logiikkaan

ESIMERKKI INTEGRAATIOSTA:

```javascript
async function analyzeOptions(question, options) {
  const response = await fetch('/api/templates/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Kipina-Sandbox-Id': window.__KIPINA_SANDBOX_ID__
    },
    body: JSON.stringify({
      question: question,
      options: options,
      analysis_type: 'pros_cons',
      language: 'fi'
    })
  });
  return response.json();
}
```

ÄLÄ:
- Yritä kutsua Gemini-mallia suoraan prototyyppi-HTML:stä — avain ei
  ole käytettävissä
- Käytä muita ulkoisia API:ja kuten OpenAI tai vastaavia
- Pyydä käyttäjältä API-avainta

window.__KIPINA_SANDBOX_ID__ on Kipinän asettama globaali muuttuja
joka sisältää nykyisen sandbox_id:n. Käytä sitä header-arvona.
```

**HUOMIO frontend-integraatiosta:** Mestarin generoima koodi käyttää `window.__KIPINA_SANDBOX_ID__` -globaalia muuttujaa. Tämä pitää **lisätä Kipinän frontendiin** myöhemmin C-vaiheen yhteydessä (esim. iframen `srcdoc`-attribuutin generoinnin yhteydessä injektoidaan tämä script). B2a:ssa tämä toimii niin että Mestari ehkä rakentaa kutsut, mutta sandbox_id puuttuu — testaa endpoint suoraan curlilla.

---

## 10. Acceptance criteria

Codex on valmis kun KAIKKI alla olevat ovat tosia:

1. `docker compose build template-proxy` rakentaa ilman virheitä
2. `docker compose up -d` käynnistää palvelun, `docker ps` näyttää `kipina-template-proxy` healthy
3. `curl http://localhost:8085/api/templates/health` palauttaa `{"ok": true, "service": "kipina-template-proxy", "templates": ["analyze"]}`
4. `curl https://pilot.kipina.digiter.fi/api/templates/health` palauttaa saman (Caddy reitittää)
5. `curl https://pilot.kipina.digiter.fi/api/prototype/health` palauttaa edelleen Prototype API:n vastauksen (ei rikottu)
6. `curl https://pilot.kipina.digiter.fi/api/concepts/health` palauttaa edelleen Concept API:n vastauksen
7. `curl https://pilot.kipina.digiter.fi/api/health` palauttaa edelleen Reveal-proxyn vastauksen
8. Smoke-test pros_cons:
```bash
curl -X POST https://pilot.kipina.digiter.fi/api/templates/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Kipina-Sandbox-Id: test-sandbox-001' \
  -d '{
    "question": "Mitä söisin tänään?",
    "options": ["Nakkiperunamuusi", "Pakastepizza"],
    "analysis_type": "pros_cons",
    "language": "fi"
  }'
```
Palauttaa 200 OK JSON:in jossa on `options`-array, jokaisella elementillä `label`, `pros` ja `cons` -kentät.
9. Smoke-test advice, ranking ja summary toimivat omilla rakenteellisilla vastauksillaan
10. Rate limiting toimii: 100 peräkkäistä kutsua samalla sandbox-id:llä palauttaa 200, 101. kutsu palauttaa 429 retry_after_seconds-kentän kanssa
11. Globaali rate limit toimii (testattavissa nostamalla raja-arvoa väliaikaisesti pieneksi)
12. Lokit näyttävät yhden rivin per request, sisältäen sandbox_id:n mutta ei query/response-sisältöä
13. Virheet (rikkinäinen JSON, puuttuva field) palautuvat 400:lla ja selkeällä virheviestillä
14. CORS-headerit asettuvat oikein OPTIONS-pyynnössä Origin: null:lle

---

## 11. Smoke-testaus jokaiselle analysis_typelle

Kun perustoiminta on saatu pystyyn, käytä näitä komentoja varmistaaksesi että kaikki neljä analysis_typeä toimivat:

```bash
# pros_cons (perustestit yllä)

# ranking
curl -X POST https://pilot.kipina.digiter.fi/api/templates/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Kipina-Sandbox-Id: test-ranking' \
  -d '{
    "question": "Mitä urheilulajia kokeilisin?",
    "options": ["Tennis", "Salibandy", "Yoga", "Hiihto"],
    "analysis_type": "ranking",
    "language": "fi"
  }'

# advice
curl -X POST https://pilot.kipina.digiter.fi/api/templates/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Kipina-Sandbox-Id: test-advice' \
  -d '{
    "question": "Pitäisikö opiskella vai mennä kavereiden kanssa?",
    "options": ["Opiskella kokeeseen", "Mennä kavereiden kanssa"],
    "analysis_type": "advice",
    "language": "fi"
  }'

# summary
curl -X POST https://pilot.kipina.digiter.fi/api/templates/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Kipina-Sandbox-Id: test-summary' \
  -d '{
    "question": "Mitä tehdä viikonloppuna?",
    "options": ["Pelata", "Lukea", "Treenata"],
    "analysis_type": "summary",
    "language": "fi"
  }'
```

Tarkista että jokainen palauttaa odotetun rakenteen luvun 4.1 mukaisesti.

---

## 12. Mitä lipata Tomille ennen valmistumista

Pyydä tarkennusta jos:

- Gemini Flashin `gemini-2.5-flash` ei ole saatavilla GCP-projektissa — kokeile `gemini-2.0-flash` tai vastaavaa, raportoi käytetty malli
- IAM-rooli `aiplatform.user` ei riitä Flash-kutsuihin (epätodennäköistä, Prototype API käyttää samaa SA:ta)
- CORS asetus tuottaa ongelmia iframen `Origin: null` -pyynnöissä — testaa selaimesta
- response_schema rajoittaa Gemini Flashia odottamattomalla tavalla — jos tulee parsing-virheitä, raportoi koko ketju

---

## 13. Mitä EI tehdä B2a:ssa (B2b:hen myöhemmin)

- Loput 12 templatea (sää, joukkoliikenne, kartat, kuvat, sitaatit, käännös, jne.)
- Pysyvä rate limit -tietokanta
- Yksityiskohtaisempi authentication
- `window.__KIPINA_SANDBOX_ID__` -injektio frontendissä (C-puolelle)
- Mestarin tarkempi Instructions kaikille templateille (vain analyze tässä vaiheessa)

---

## 14. Viittaukset

- B-dokumentti: `kipina-vibe-B-backend.md` (Template Library -kuvaus luvuissa 4 ja 6.5)
- A-dokumentti: `kipina-vibe-A-konsepti.md` (luku 6.5 Template Library -periaate)
- Esimerkki vastaavasta palvelusta: `apps/concept-api/` (Gemini-kutsun rakenne) ja `apps/prototype-api/` (palvelun rakenne, lokitus, env-muuttujat)

---

**Brief loppuu.** Aloita lukemalla `apps/concept-api/app.py` koodityyliksi referenssiksi (Gemini-kutsujen rakenne) ja `apps/prototype-api/app.py` palvelinrakenteen pohjaksi (ThreadingHTTPServer, env-muuttujat, lokitus). Jos jokin yllä on epäselvää, pyydä tarkennusta sen sijaan että arvaat.
