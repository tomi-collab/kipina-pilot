# Kipinä Vibe — B. Backend

**Dokumentti:** B/3 (Backend)
**Päivätty:** 2026-05-28
**Kirjoittaja:** Tomi Turpeinen + Claude (suunnittelukeskustelu)
**Tila:** Luonnos kommentoitavaksi
**Edellyttää:** A-dokumentti hyväksytty

---

## 1. Yleiskuva

Vibekoodausvaihe tuo Kipinään **kolme uutta backend-palvelua** ja yhden ulkoisen GCP-resurssin. Kaikki palvelut noudattavat samoja periaatteita kuin nykyiset palvelut (Reveal Data API ja Concept API): pure stdlib Python `http.server`, oma kontaineri, `127.0.0.1`-binding, Caddy-reititys, JSON-input/output.

| Palvelu | Portti (host) | Vastuu | Stack |
|---------|---------------|--------|-------|
| Prototype API | 8083 | Vertex AI Agent Engine -kutsut, sandbox-elinkaari, Mestarin system instructions | Python + `google-genai` SDK |
| STT Proxy | 8084 | Google Cloud Speech-to-Text -välitys | Python + `google-cloud-speech` |
| Template API Proxy | 8085 | Ulkoiset API-templatet, avainten piilotus, rate limiting | Python (lähinnä proxy) |

**Ulkoinen GCP-resurssi:**

| Resurssi | Sijainti | Vastuu |
|----------|----------|--------|
| Vertex AI Agent Engine -instanssi | `us-central1` | Mestarin sandbox-suoritusympäristö |

### Domain ja reititys

Kaikki uusi liikenne kulkee saman domainin alta: `pilot.kipina.digiter.fi`. Caddy reitittää:

```
pilot.kipina.digiter.fi {
    handle /api/prototype/*  { reverse_proxy localhost:8083 }
    handle /api/stt/*        { reverse_proxy localhost:8084 }
    handle /api/templates/*  { reverse_proxy localhost:8085 }
    handle /api/concepts/*   { reverse_proxy localhost:8082 }  # olemassa
    handle /api/*            { reverse_proxy localhost:8081 }  # reveal-data-api
    handle                   { reverse_proxy localhost:8080 }  # frontend
}
```

**Tärkeää:** Caddy matchaa järjestyksessä, joten **uudet spesifit reitit pitää lisätä ENNEN olemassa olevia geneerisempiä reittejä** (`/api/*`). Tämä on sama logiikka kuin Concept API:n lisäyksessä.

---

## 2. Prototype API

### 2.1 Tarkoitus

Prototype API on Kipinän silta Vertex AI Agent Engineen. Se:
- Luo ja hallinnoi sandboxeja (yksi per vibekoodausistunto)
- Välittää käyttäjän pyynnöt Mestarille (LLM + Code Execution)
- Palauttaa frontendille uuden prototyyppi-HTML:n tai Pohdinta-vastauksen
- Pitää kirjaa istunnon iteraatiohistoriasta sandboxin elinajan

### 2.2 Endpointit

#### `POST /api/prototype/start`

Aloittaa uuden vibekoodausistunnon.

**Request:**
```json
{
  "concept": "string — Concept API:n tuottama konsepti",
  "report": "string — alkuperäinen Reveal-raportti",
  "tenant_id": "string — esim. 'maailma'",
  "session_id": "string — frontendin generoima uniikki id"
}
```

**Behavior:**
1. Validoi että `concept` ja `report` ovat ei-tyhjiä, max 50 000 merkkiä kumpikin
2. Luo uusi Code Execution -sandbox Vertex AI Agent Engineen
3. Tallenna `sandbox_id` ↔ `session_id` -mappaus muistiin (Python-dictionary aluksi, ei Redis pilotissa)
4. Kutsu Mestaria luomaan **ensimmäinen prototyyppiversio** konseptin pohjalta (yksitiedostoinen HTML)
5. Palauta versio ja sandbox-tiedot

**Response 200:**
```json
{
  "sandbox_id": "string — käytetään seuraavissa kutsuissa",
  "prototype_html": "string — yksitiedostoinen HTML iframea varten",
  "mestari_message": "string — esim. 'Tein ensimmäisen luonnoksen, mitä mieltä?'",
  "ttl_seconds": 3600
}
```

**Errors:**
- 400: validointivirhe
- 502: Vertex AI -virhe (sandbox-luonti epäonnistui, LLM ei vastannut)
- 503: sandbox-kiintiö täynnä (käytä uudelleen myöhemmin)

#### `POST /api/prototype/iterate`

Yksi iteraatio Mestarin kanssa Koodaus- tai Pohdinta-tilassa.

**Request:**
```json
{
  "sandbox_id": "string",
  "mode": "koodaus" | "pohdinta",
  "user_input": "string — käyttäjän pyyntö (puheesta tai tekstinä)",
  "language": "fi" | "en"
}
```

**Behavior — Koodaus-tila:**
1. Validoi sandbox elossa ja kuuluu sessiolle
2. Lähetä Mestarille: nykyinen prototyypin tila + iteraatiohistoria + uusi pyyntö + Template Library -kuvaus
3. Mestari muokkaa koodia sandboxissa
4. Palauta uusi HTML + Mestarin lyhyt kommentti

**Behavior — Pohdinta-tila:**
1. Validoi sandbox elossa
2. Lähetä Mestarille pelkkä keskustelukysymys (ei koodimuutosta)
3. Palauta Mestarin tekstivastaus, älä päivitä prototyyppiä

**Response 200 (Koodaus):**
```json
{
  "prototype_html": "string — uusi HTML",
  "mestari_message": "string — esim. 'Vaihdoin värin vihreäksi.'",
  "iteration_count": 5
}
```

**Response 200 (Pohdinta):**
```json
{
  "mestari_message": "string — pidempi vastaus, ei HTML:ää",
  "iteration_count": 5
}
```

#### `GET /api/prototype/history/{sandbox_id}`

Palauttaa session-aikaisen iteraatiohistorian frontendille näytettäväksi. Tämä on tärkeä "mitä mä äsken sanoin" -tarpeelle — nuoret pystyvät palauttamaan mieleen viimeisimmät pyyntönsä ilman että historia tallennetaan pysyvästi.

**Request:** vain `sandbox_id` URL-parametrina, ei body:ä.

**Behavior:**
1. Tarkista että sandbox elossa ja kuuluu sessiolle
2. Hae `recent_iterations`-lista sandbox-statesta
3. Palauta lista uusin ensin -järjestyksessä

**Response 200:**
```json
{
  "sandbox_id": "string",
  "iterations": [
    {
      "user_input": "string",
      "mestari_message": "string",
      "mode": "koodaus" | "pohdinta",
      "iteration_number": 5,
      "timestamp": "2026-05-28T14:23:11Z"
    },
    ...
  ],
  "total_iterations": 12
}
```

`iterations`-lista palauttaa max 20 viimeisintä. `total_iterations` kertoo todellisen kokonaismäärän jos halutaan näyttää frontendissä "näytät 20/35".

**Errors:** 404 jos sandbox-tunnusta ei löydy.

#### `POST /api/prototype/undo`

Palaa edelliseen prototyyppiversioon. Pilotissa undo-historia on muistissa (Prototype API:n process memory), ei tallennettuna pysyvästi. Häviää palvelun restartissa.

**Request:**
```json
{
  "sandbox_id": "string"
}
```

**Behavior:**
1. Tarkista että sandbox elossa
2. Hae edellinen HTML-versio in-memory historiasta
3. Päivitä Mestarin kontekstiin että käyttäjä peruutti edellisen muutoksen
4. Palauta edellinen versio + Mestarin lyhyt kuittaus

**Response 200:**
```json
{
  "prototype_html": "string — edellinen versio",
  "mestari_message": "string — esim. 'Palautin edellisen.'",
  "iteration_count": 4,
  "undo_available": true
}
```

**Response 400** jos undo-historiaa ei ole (ensimmäinen versio):
```json
{
  "error": "no_undo_available",
  "message": "Tämä on ensimmäinen versio, ei voi peruuttaa."
}
```

#### `POST /api/prototype/remind-check`

Mestarin "muistutusmekanismi" konseptiuskollisuudesta. Frontend voi kutsua tätä silloin tällöin (esim. 10. iteraation jälkeen) kysyäkseen Mestarilta, ollaanko vielä konseptin alueella.

**Request:**
```json
{
  "sandbox_id": "string"
}
```

**Response:**
```json
{
  "should_remind": true | false,
  "reminder_message": "string — vain jos should_remind=true"
}
```

#### `DELETE /api/prototype/{sandbox_id}`

Päättää session aktiivisesti. Poistaa sandboxin ja vapauttaa resurssit.

#### `POST /api/prototype/suggest-iteration`

**Testaustyökalu — vain superadmin-roolille.** Generoi ehdotetun seuraavan iteraatiopyynnön testaajalle, jonka tämä voi muokata ja lähettää normaalin `/iterate`-endpointin kautta. Käytetään Mestarin manuaaliseen testaukseen.

**Request:**
```json
{
  "sandbox_id": "string",
  "count": 1 | 2 | 3
}
```

**Validointi:**
- `sandbox_id` löytyy muistista
- Pyynnön headerissa `X-Kipina-Role: superadmin` ja oikea `X-Kipina-Superadmin-Key` ympäristömuuttujan `KIPINA_SUPERADMIN_KEY` mukaisesti — muuten 403 Forbidden
- `count` 1–3, oletus 1

**Behavior:**
1. Tarkista superadmin-rooli ja avain
2. Hae sandbox-tila: konsepti, nykyinen HTML, viimeisimmät iteraatiot
3. Kutsu Gemini-mallia (sama `gemini-2.5-pro`, eri system instruction kuin Mestarilla)
4. System instruction generaattorille (vapaasti muokattavissa kehityksessä):
   ```
   Olet testausagentti Kipinän pilotissa. Tehtäväsi on generoida
   uskottavia käyttäjäpyyntöjä nuorten kielellä, joilla Mestaria
   voidaan testata. Pyydä yksinkertaisia muutoksia prototyyppiin:
   värimuutoksia, layout-säätöjä, uusien elementtien lisäämistä,
   tekstin muokkauksia. Saa käyttää keksittyjä nimiä ja paikkoja
   — niitä ei suodateta täällä, ne käytetään Mestarin DLP-mekanismin
   testaamiseen.
   Pidä pyynnöt lyhyinä (1–2 lausetta) ja luonnollisina.
   ```
5. Palauta lista ehdotuksia

**Response 200:**
```json
{
  "suggestions": [
    "Lisää sääikoni etusivulle ja tee siitä keltainen.",
    "Vaihda kaikki napit pyöreäksi.",
    "Lisää 'Tervetuloa, Amina!' -tervehdys ylälaitaan."
  ]
}
```

**Tärkeä toteutushuomio koodaajalle (auditoitava poikkeus):**

Tämä endpoint **EI aja DLP:tä** ennen Gemini-kutsua eikä sen jälkeen. Tämä on tarkoituksellinen ja dokumentoitu valinta:

- Generoidut pyynnöt voivat sisältää keksittyjä henkilönimiä ja paikkoja
- DLP:n oikea testipaikka on Prototype API:n `/iterate`-endpoint, jonne ehdotus joka tapauksessa päätyy
- Jos DLP suodattaisi nimet ennen Geminiä tai sen jälkeen, DLP:n toimintaa ei voisi testata realistisilla syötteillä
- Pääsy on rajattu superadmin-rooliin, ei loppukäyttäjäpolku

**Älä lisää DLP-suodatusta tähän endpointiin "korjauksena".** Jos uuden version kehittäjälle tämä tuntuu väärältä, lue tämä kommentti ensin ja tarkista A-dokumentin "Auditoidut poikkeukset" -osio.

**Errors:**
- 403 jos superadmin-rooli puuttuu
- 404 jos sandbox-tunnusta ei löydy
- 502 Gemini-virhe

#### `GET /api/prototype/health`

Standardi terveyscheck. Palauttaa `{"ok": true, "service": "kipina-prototype-api"}`.

### 2.3 Sandbox-elinkaari ja versiohistoria

- **TTL alkuvaiheessa**: 3600 sekuntia (1h)
- **Luonti**: `/start`-kutsun yhteydessä
- **Poisto**: aktiivinen `/delete`-kutsu TAI TTL umpeutuu (Google poistaa automaattisesti)
- **Tila muistissa**: Python-dictionary `sandbox_id → {session_id, created_at, iteration_count, html_history}`. Jos palvelu käynnistyy uudelleen, muistitila katoaa mutta sandboxit jäävät elämään GCP:hen TTL:nsä loppuun. Tämä on hyväksytty pilottirajoitus.

**Versiohistoria undoa varten:**

`html_history` on lista viimeisimmistä HTML-versioista, max 20 viimeisintä per sandbox. Tämä mahdollistaa `/undo`-toiminnon ilman GCS:ää tai muuta pysyvää tallennusta. Pilotin oletetuilla istuntopituuksilla (10–20 iteraatiota) 20 askeleen historia kattaa käytännössä koko session.

Suunnittelusyy: pilotissa undo on tärkeä käyttäjäkokemuksen kannalta ("mä menin liian pitkälle"), mutta sandboxin kaatumisesta palautuminen ja iteraatiolinkkien jako eivät ole pilotin oppimistavoitteita. Jos pilotti onnistuu ja tarvitaan kestävämpi ratkaisu, undo-endpoint pysyy samana mutta `html_history` voidaan myöhemmin siirtää Cloud Storageen ilman API-muutoksia.

### 2.4 Mestarin LLM-malli

- Malli: `gemini-3-pro` (sama kuin Concept API:lla)
- Sijainti: `us-central1` (Agent Engine vaatii tämän)
- Pääsy: sama service account kuin Concept API:lla, mutta tarvittaessa erillinen (luvussa 6)

### 2.5 Iteraatiokontekstin koko

Mestarille välitetään joka kutsulla:
- System instructions (kiinteä, ks. luku 5)
- Konsepti (kiinteä koko session ajan)
- Reveal-raportti (kiinteä koko session ajan)
- Nykyinen prototyypin HTML (vaihtuu joka iteraatiossa)
- Viimeisimmät iteraatiot (rolling window, **20 viimeisintä** — tukee "mitä mä äsken sanoin" -ominaisuutta frontendissä)
- Template Library -kuvaus (kiinteä)
- Käyttäjän uusi pyyntö

Tokenien hallinta: 20 iteraation lista on Geminin 1M-kontekstissa täysin mitätön (arviolta 5-10K tokenia). Pilotin pituuksissa (10–30 iteraatiota) koko historia mahtuu hyvin kontekstiin ilman tiivistystä. Jos tarve nousee myöhemmin, tiivistys voidaan tehdä joka 20. iteraation jälkeen erillisellä Gemini Flash -kutsulla.

### 2.6 Tiedostorakenne

```
apps/prototype-api/
├── app.py              # HTTP-palvelin (ThreadingHTTPServer)
├── mestari.py          # System instructions, prompt-rakentaminen
├── agent_engine.py     # Vertex AI Agent Engine SDK -kääre
├── sandbox_state.py    # sandbox_id ↔ session_id -muistitila
├── templates.py        # Template Library -kuvaus (luetaan B.4:n JSON:ista)
├── Dockerfile
└── requirements.txt
```

### 2.7 requirements.txt

```
google-genai>=1.0.0
google-cloud-aiplatform>=1.112.0
```

`google-cloud-aiplatform` tarvitaan Agent Engine -sandbox-API:lle, koska `google-genai` ei vielä tue sitä natiivisti (vrt. avoin issue js-genai:ssa).

### 2.8 docker-compose.yml -lisäys

```yaml
prototype-api:
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
    AGENT_ENGINE_ID: "projects/apply-project-35406/locations/us-central1/reasoningEngines/<id>"
    GOOGLE_APPLICATION_CREDENTIALS: "/secrets/gcp-sa-vibe.json"
    TEMPLATE_LIBRARY_PATH: "/app/templates.json"
  volumes:
    - ./secrets/gcp-sa-vibe.json:/secrets/gcp-sa-vibe.json:ro
    - ./apps/prototype-api/templates.json:/app/templates.json:ro
```

---

## 3. STT Proxy

### 3.1 Tarkoitus

Frontendin mikkinappula nauhoittaa ääntä, lähettää sen Kipinään, joka välittää sen Google Cloud Speech-to-Textille ja palauttaa litteroidun tekstin. Avain pysyy palvelimella.

### 3.2 Endpointit

#### `POST /api/stt/transcribe`

Litteroi äänitiedoston tekstiksi.

**Request:** `multipart/form-data` jossa kentät:
- `audio`: äänitiedosto (webm/opus tai mp3, max 60 sekuntia, max 10 MB)
- `language`: `fi-FI` (oletus) tai `en-US`

**Behavior:**
1. Validoi tiedoston koko ja kesto
2. Kutsu Google Cloud Speech-to-Text Streaming API
3. Palauta litteroinnin paras tulos

**Response 200:**
```json
{
  "transcript": "string — litteroitu teksti",
  "confidence": 0.92,
  "language": "fi-FI"
}
```

**Errors:**
- 400: tiedosto liian iso tai väärässä formaatissa
- 413: yli 60 sekuntia ääntä
- 502: Google STT -virhe

#### `GET /api/stt/health`

Terveyscheck.

### 3.3 Streaming vai batch?

Pilotin yksinkertainen versio: **batch-STT** (push-to-talk → koko äänitiedosto kerralla). Tämä riittää rautalangan "pidä pohjassa ja puhu" -mallille.

Tulevaisuudessa voidaan harkita **streaming-STT**:tä (puhe litteroidaan reaaliajassa puhuessa), mutta se vaatii WebSocketin tai Server-Sent Eventsiä, ja pilotissa ei vielä mennä siihen.

### 3.4 Tiedostorakenne

```
apps/stt-proxy/
├── app.py
├── Dockerfile
└── requirements.txt
```

### 3.5 requirements.txt

```
google-cloud-speech>=2.27.0
```

### 3.6 docker-compose.yml -lisäys

```yaml
stt-proxy:
  build:
    context: ./apps/stt-proxy
  container_name: kipina-stt-proxy
  restart: unless-stopped
  ports:
    - "127.0.0.1:8084:8080"
  environment:
    GCP_PROJECT_ID: "apply-project-35406"
    GCP_LOCATION: "europe-west4"  # STT toimii useissa alueissa, pidetään lähellä käyttäjää
    GOOGLE_APPLICATION_CREDENTIALS: "/secrets/gcp-sa-vibe.json"
  volumes:
    - ./secrets/gcp-sa-vibe.json:/secrets/gcp-sa-vibe.json:ro
```

---

## 4. API Template Library + Template Proxy

### 4.1 Periaate

Mestari saa kutsua **vain tämän proxyn kautta** ulkoista dataa. Suorat kutsut muualle iframen koodista on kielletty Mestarin system instructionseissa.

Proxy:
1. Tarjoaa Kipinän oman domainin alta endpointit kullekin templatille
2. Lisää API-avaimet palvelinpuolella jos tietolähde vaatii
3. Rajoittaa kutsumäärää per `sandbox_id` (header `X-Kipina-Sandbox-Id`) — esim. max 100 kutsua per sandbox per tunti
4. Palauttaa standardisoidun JSON-muodon kaikille templateille

### 4.2 Template-formaatti (`templates.json`)

Jokainen template kuvataan JSON-tiedostossa joka latautuu sekä Template Proxylle (datalähteenä) että Prototype API:lle (Mestarin system instructionseihin liitettäväksi).

```json
{
  "templates": [
    {
      "id": "weather-current",
      "category": "weather",
      "description": "Nykyinen säätila annetulle paikkakunnalle Suomessa.",
      "input_schema": {
        "place": "string — paikkakunnan nimi suomeksi, esim. 'Helsinki'"
      },
      "endpoint": "/api/templates/weather-current",
      "example_response": {
        "place": "Helsinki",
        "temperature_c": 4.2,
        "description": "puolipilvistä",
        "wind_ms": 3.1,
        "humidity_pct": 78
      },
      "use_for": [
        "säätieto",
        "weather data",
        "ulkona oleva"
      ],
      "external_source": "ilmatieteenlaitos avoin data",
      "cost_per_call_eur": 0.0
    },
    {
      "id": "transit-helsinki",
      "category": "transit",
      "description": "Seuraavat lähdöt annetulta pysäkiltä Helsingissä (HSL).",
      "input_schema": {
        "stop_name": "string — pysäkin nimi, esim. 'Rautatientori'"
      },
      "endpoint": "/api/templates/transit-helsinki",
      "example_response": {
        "stop": "Rautatientori",
        "departures": [
          { "line": "9", "destination": "Pasila", "minutes": 3 },
          { "line": "6T", "destination": "Hietalahti", "minutes": 5 }
        ]
      },
      "use_for": ["joukkoliikenne", "transit", "bussi", "ratikka"],
      "external_source": "HSL Digitransit",
      "cost_per_call_eur": 0.0
    }
  ]
}
```

### 4.3 Pilotin ensimmäinen template-lista (10–15 kpl)

Valittu kattamaan yleisimmät tarpeet, joita Concept API tyypillisesti tuottaa "Tarvittavat tietovirrat" -osiossa.

| ID | Kategoria | Kuvaus | Lähde | Kustannus |
|----|-----------|--------|-------|-----------|
| `weather-current` | Sää | Nykyinen säätila paikkakunnalle | Ilmatieteenlaitos avoin data | Ilmainen |
| `weather-forecast` | Sää | Viikon ennuste paikkakunnalle | Ilmatieteenlaitos | Ilmainen |
| `transit-helsinki` | Liikenne | HSL:n pysäkkilähdöt | Digitransit | Ilmainen |
| `transit-finland` | Liikenne | Junat/bussit muualla Suomessa | Digitransit waltti | Ilmainen |
| `map-static` | Kartta | Staattinen karttakuva paikalle | OpenStreetMap | Ilmainen |
| `image-random` | Kuva | Satunnainen kuva aiheella | Lorem Picsum / Unsplash Source | Ilmainen |
| `quote-random` | Teksti | Satunnainen suomenkielinen sitaatti | Oma kovakoodattu lista | Ilmainen |
| `fact-random` | Teksti | Satunnainen fakta valitulta alueelta | Oma kovakoodattu lista | Ilmainen |
| `dictionary-fi` | Sanakirja | Suomen kielen sanan selitys | Kotus avoin data | Ilmainen |
| `translate` | Kääntäjä | Käännös fi↔en | Google Translate API | ~0,01€/1000 merkkiä |
| `news-headlines` | Uutiset | Yle:n RSS-otsikot kategorian mukaan | Yle RSS | Ilmainen |
| `calendar-mock` | Mock-data | Simuloitu käyttäjäkalenteri viikolle | Generoitu palvelimella | Ilmainen |
| `messages-mock` | Mock-data | Simuloituja viestejä keskustelusta | Generoitu palvelimella | Ilmainen |
| `location-finland` | Mock-data | Satunnainen sijainti Suomessa | Generoitu palvelimella | Ilmainen |

13 templatea, joista 1 maksullinen (Translate). Käännösbudjetti rajoitetaan proxyssä per sandbox.

### 4.4 Mock-datan periaate

Mock-templatet (`calendar-mock`, `messages-mock`, `location-finland`) palauttavat **uskottavaa mutta keksittyä** dataa. Esimerkki `calendar-mock`-vastauksesta:

```json
{
  "week_starts": "2026-06-02",
  "events": [
    { "day": "ma", "time": "10:00", "title": "Matematiikka" },
    { "day": "ma", "time": "14:00", "title": "Kavereiden kanssa kahville" },
    { "day": "ti", "time": "08:30", "title": "Treenit" }
  ]
}
```

Ei käytä todellisia henkilötietoja, ei oikeita kalentereita, mutta tuntuu sovelluksessa eläväksi. Mock-data on sama jokaisella kutsulla (deterministinen) jotta Mestari voi suunnitella UI:n sen perusteella.

### 4.5 Rate limiting

- **Per sandbox**: 100 kutsua/h kokonaisuudessaan, 20 kutsua/h kalliimmille templateille (`translate`)
- **Globaali**: 10 000 kutsua/päivä proxyn yli kaikkien sandboxien kesken
- **Toteutus pilotissa**: in-memory dictionary `{sandbox_id: {timestamp: count}}`. Yksinkertainen, hukataan kun palvelu käynnistyy uudelleen. Riittää pilotille.

### 4.6 Tiedostorakenne

```
apps/template-proxy/
├── app.py                  # HTTP-palvelin + rate limiter
├── templates.json          # Kanoninen template-lista (kopioidaan myös Prototype API:lle)
├── handlers/
│   ├── weather.py
│   ├── transit.py
│   ├── map.py
│   ├── image.py
│   ├── quote.py
│   ├── fact.py
│   ├── dictionary.py
│   ├── translate.py
│   ├── news.py
│   └── mock.py             # calendar-mock, messages-mock, location-finland
├── Dockerfile
└── requirements.txt
```

### 4.7 requirements.txt

```
google-cloud-translate>=3.15.0  # vain translate-templatea varten
```

Useimmat templatet käyttävät pelkkää `urllib`:ia stdlib:istä, joten ulkoisia riippuvuuksia on vähän.

### 4.8 docker-compose.yml -lisäys

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
    GOOGLE_APPLICATION_CREDENTIALS: "/secrets/gcp-sa-vibe.json"
    # Mahdolliset muut API-avaimet (esim. Unsplash) tähän tai .env:iin
  volumes:
    - ./secrets/gcp-sa-vibe.json:/secrets/gcp-sa-vibe.json:ro
```

---

## 5. Mestarin system instructions

Tämä on B-dokumentin tärkein osio. Mestarin "persoona" ja toimintaperiaatteet määritellään ennen kaikkea näiden ohjeiden kautta.

### 5.1 Pohjarakenne

System instructionsit rakentuvat kuudesta osasta, jotka kootaan dynaamisesti joka iteraatiossa:

```
1. Mestarin perusrooli ja äänensävy        (kiinteä)
2. Tehtävänkuva ja toimintaperiaatteet     (kiinteä)
3. Template Library -kuvaus                (kiinteä, luetaan templates.json:sta)
4. Konsepti                                (kiinteä session ajan)
5. Reveal-raportti                         (kiinteä session ajan)
6. Iteraatiohistoria + nykyinen prototyyppi (vaihtuu)
```

Käyttäjän pyyntö lähetetään `contents`-osiossa erikseen.

### 5.2 Mestarin perusrooli — kiinteä teksti

```
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
```

### 5.3 Tehtävänkuva — kiinteä teksti

```
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
  riippuvuuksia paitsi Template Libraryn endpointit
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
```

### 5.4 Template Library -kuvaus — generoidaan templates.json:sta

Jokaisessa iteraatiossa system instructionseihin liitetään tiivistetty kuvaus käytettävissä olevista templateista. Generointi tehdään Pythonissa luettaessa templates.json:

```
KÄYTETTÄVISSÄ OLEVAT TIETOLÄHTEET:

Voit kutsua näitä endpointeja prototyypin koodista. Et koskaan
käytä mitään muita ulkoisia osoitteita.

[weather-current] — Nykyinen säätila paikkakunnalle Suomessa
  GET /api/templates/weather-current?place=<paikkakunta>
  Esim: { "place": "Helsinki", "temperature_c": 4.2,
          "description": "puolipilvistä", "wind_ms": 3.1 }
  Soveltuu: säätieto, weather data, ulkona oleva

[transit-helsinki] — Seuraavat lähdöt pysäkiltä Helsingissä
  GET /api/templates/transit-helsinki?stop_name=<nimi>
  Esim: { "stop": "Rautatientori",
          "departures": [{"line": "9", "minutes": 3}] }
  Soveltuu: joukkoliikenne, transit, bussi, ratikka

[... loput 11 templatea samalla rakenteella ...]

VALINTAOHJE:

- Lue konseptin "Tarvittavat tietovirrat" -osio
- Valitse templatet jotka vastaavat sitä
- Jos tarpeelle ei ole templatea, simuloi staattisella mockilla
  HTML:n sisällä ja merkitse selvästi: "Demo-data"
- Käytä mock-templateja (calendar-mock, messages-mock,
  location-finland) kun konsepti vaatii käyttäjän omaa dataa
  jota ei pilotissa voi oikeasti hakea
```

### 5.5 Konsepti ja raportti

Liitetään sellaisenaan system instructionseihin, otsikoituna:

```
ALKUPERÄINEN KONSEPTI (Concept API:n tuottama):

<concept-teksti>

ALKUPERÄINEN REVEAL-RAPORTTI (nuoren oma keskustelu):

<report-teksti>
```

### 5.6 Iteraatiohistoria + nykyinen prototyyppi

```
NYKYINEN PROTOTYYPPI:

<koko HTML viimeisimmästä versiosta>

VIIMEISIMMÄT ITERAATIOT:

1. Käyttäjä: "Tee tästä vihreä"
   Mestari: Vaihdoin pohja-värin vihreäksi.

2. Käyttäjä: "Lisää sääikoni"
   Mestari: Lisäsin auringonpaiste-ikonin yläkulmaan.

[... max 5 viimeisintä ...]
```

Jos iteraatioita on enemmän kuin 5, generoidaan tiivistys vanhemmista (luvussa 2.5).

### 5.7 Output-formaatti Mestarille

Mestarin pitää palauttaa **strukturoitu JSON**, ei vapaata tekstiä:

```json
{
  "mode": "koodaus" | "pohdinta",
  "prototype_html": "string — vain jos mode=koodaus",
  "mestari_message": "string — lyhyt kommentti tai keskusteluvastaus",
  "concept_drift_warning": false | "string — jos Mestari huomaa ajautumista konseptista"
}
```

Tämä toteutetaan Geminin response schema -ominaisuudella jotta output on aina oikein parsittavissa.

### 5.8 Mestarin Tools — Grounding with Google Search ja URL Context

Vertex AI Agent Engine (osana Gemini Enterprise Agent Platformia, entinen Vertex AI) tarjoaa natiiveja työkaluja jotka voidaan aktivoida Agent Builderin UI:sta (Tools-osio). Pilotissa Mestarille aktivoidaan **kaksi natiivia työkalua**:

- **Grounding with Google Search** — Mestari voi hakea reaaliaikaista tietoa verkosta generointihetkellä, ja Geminin vastaukset "groundataan" oikeisiin hakutuloksiin
- **URL Context** — Mestari voi hakea ja lukea verkkosivujen sisältöä (Agent Builderissa oletusarvoisesti enabled)

Nämä eivät korvaa Template Proxya (B2) vaan täydentävät sitä eri käyttötapauksiin:

| Työkalu | Käyttöaika | Käyttötapaus |
|---------|-----------|--------------|
| Grounding with Google Search / URL Context | **Generointihetkellä** (Mestarin agentti-ajo) | Designinspiraatio, kontekstitieto, esimerkki-UI:t, paras käytäntö -tieto |
| Template Proxy | **Runtime-aikaisesti** (prototyypin selaimessa) | Reaaliaikainen data jonka nuori näkee kun avaa prototyypin |

Esimerkki erosta: Jos Mestari rakentaa sääsovellusta:
- **Grounding with Google Search** auttaa Mestaria päättämään minkätyyppinen UI on tyypillistä sääsovelluksissa, mitä ikoneita käytetään, miten layout järjestyy
- **Template Proxy** kytketään HTML:ään niin että nuori näkee oikean säätilan kun hän avaa sovelluksen

> **Tulevaisuuden mahdollisuus B2:lle:** Agent Builder tukee myös Model Context Protocol (MCP) -palvelimia, joiden kautta omia työkaluja voidaan rekisteröidä Mestarille function callingina. Jos B2:n Template Proxy rakennetaan MCP-palvelimena, Mestari voi kutsua templatekutsuja generointihetkellä eikä vain runtime-aikaisesti. Tämä on harkittavissa B2-vaiheessa — pidetään mielessä mutta ei tehdä päätöstä vielä.

#### Aktivointi

Agent Builderissa (`Kipina-Mestari` Agent), Tools-osio:
1. Grounding with Google Search → Enabled
2. URL Context → Enabled (todennäköisesti jo oletuksena päällä)

Ei vaadi koodimuutoksia Prototype API:hin, koska Tools ajetaan Agent Engine -tasolla.

#### System instructions -lisäys

Mestarin perusrooliin ja tehtävänkuvaan (5.2–5.3) lisätään tämä Tools-osio:

```
TYÖKALUT (Tools):

Sinulla on käytössäsi kaksi työkalua jotka voit kutsua tarpeen mukaan:

1. GOOGLE_SEARCH — hae verkosta tietoa, esimerkkejä, käytäntöjä
2. URL_CONTEXT — hae ja lue tietty verkkosivu

KÄYTÄ TYÖKALUJA:
- Kun haluat parantaa prototyypin visuaalista tai toiminnallista
  suunnittelua etsimällä inspiraatiota tai parhaita käytäntöjä
- Kun et ole varma jonkin asian standardimuodosta (esim. miten
  joukkoliikenneaikataulu yleensä esitetään)
- Kun konseptin aihealue vaatii erityistietoa jota sinulla ei ole

ÄLÄ KÄYTÄ TYÖKALUJA:
- Henkilötietojen etsimiseen — ei oikeiden henkilöiden tietoja,
  ei nuoren omiin tietoihin liittyvää hakua
- Triviaaleihin värimuutoksiin tai layoutsiirtoihin — älä googlaa
  "vihreä HEX-koodi", käytä omaa tietämystäsi
- Aikaa vievään tutkimukseen — yksi tai kaksi hakua per iteraatio
  riittää, älä tee ketjuhakua

TYÖKALUJEN TULOSTEN KÄYTTÖ:
- Tools-tulokset ovat **inspiraatiota ja kontekstia**, eivät
  prototyypin sisältöä
- Älä lisää löytämiäsi ulkoisia URL-osoitteita prototyypin
  HTML:ään
- Älä kopioi pitkiä tekstinpätkiä Tools-tuloksista — käytä omin
  sanoin
- Jos Tools palauttaa epäilyttävää, kaupallista tai sopimatonta
  sisältöä, ohita se hiljaa
```

#### Latenssin ja kustannusten huomiointi

Tools-kutsut lisäävät iteraation kestoa noin 1–3 sekuntia per kutsu, ja Tools-tulokset kuluttavat tokeneita (Google Search snippet ~500 tokenia, URL Context koko sivu jopa 5000+ tokenia).

**Karkea arvio kustannusvaikutuksesta:**
- Tools-kutsuja per iteraatio: keskimäärin 0–2
- Lisätokenikustannus: ~0,5€ per iteraatio jossa Tools käytössä
- Vaikutus 855€-budjettiin: jos 50% iteraatioista käyttää Toolsia, kokonaisbudjettiin lisätään noin 25%

Tämä on hyväksyttävä lisäys pilotissa. Jos kustannukset osoittautuvat ongelmaksi, Mestarille voidaan kiristää Tools-käytön kriteerejä system instructionseissa myöhemmin.

#### Turvallisuus

Tools-tuloksiin pätee sama periaate kuin nuoren käyttäjäsyötteeseen:
- Mestari **ei kopioi henkilötietoja** Tools-tuloksista prototyyppiin
- Mestari **ei aja löytämäänsä koodia** sandboxissa muulta kuin omasta päättelystä syntynyttä koodia
- Tools-tulokset eivät päädy lokeihin (privacy-lokitus pätee)

---

## 6. GCP-resurssit ja autentikointi

### 6.1 Service Account -strategia

Pilotissa käytetään **erillistä SA:ta vibekoodaukselle**, ei jaeta Concept API:n SA:ta. Syyt:
- Oikeudet voidaan rajata tarkasti vibekoodausvaiheelle
- Käyttö ja kustannukset näkyvät GCP:n laskutuksessa erikseen
- Mahdollinen virhe ei vaikuta Concept API:hin

SA-nimi: `kipina-vibe@apply-project-35406.iam.gserviceaccount.com`

### 6.2 IAM-roolit

| Rooli | Mihin | Miksi |
|-------|-------|-------|
| `roles/aiplatform.user` | apply-project-35406 | Gemini-kutsut + Agent Engine |
| `roles/cloudtranslate.user` | apply-project-35406 | Translate-template |
| `roles/speech.client` | apply-project-35406 | STT Proxy |

### 6.3 Avaimen sijainti palvelimella

`/opt/kipina-pilot/secrets/gcp-sa-vibe.json` (sama hakemisto kuin Concept API:n SA, mutta eri tiedosto).

`chmod 600`, gitignored.

### 6.4 Vertex AI Agent Engine -instanssin luonti

**Ennen ensimmäistä deploymenttia** projektissa pitää olla luotuna Agent Engine -instanssi `us-central1`-alueelle:

```python
from vertexai import agent_engines

agent_engine = agent_engines.create(
    display_name="kipina-mestari",
    description="Mestari — Kipinän vibekoodausagentti"
)
# Tallenna agent_engine.resource_name → AGENT_ENGINE_ID env-muuttujaan
```

Tämä tehdään kerran, manuaalisesti tai erillisellä init-skriptillä `apps/prototype-api/init/`.

### 6.5 Kiintiöt

Tarkistetaan ennen deploymenttia:
- Agent Engine sandbox -kiintiö projektissa
- Gemini 3 Pro -tokenkiintiö `us-central1`-alueella
- Speech-to-Text minuuttikiintiö

Jos pilottikäyttö ylittää oletuskiintiöt, pyydetään korotusta GCP Console -tukikanavalla.

---

## 7. Tietoturva ja yksityisyys

### 7.1 Iframen rajaus

Prototyyppi pyörii iframessa joka frontendissä **sandbox-attribuutilla**:

```html
<iframe sandbox="allow-scripts" srcdoc="..."></iframe>
```

`allow-scripts` mahdollistaa JS-suorituksen, mutta:
- Ei `allow-same-origin` → iframe ei pääse Kipinän cookieihin/localStorageen
- Ei `allow-forms` → ei lomakkeiden lähetystä ulos
- Ei `allow-popups` → ei pop-up-ikkunoita
- Ei `allow-top-navigation` → ei sivun uudelleenohjausta

Template Proxyyn pääsy iframen sisältä toimii silti, koska se on sama origin frontendin kanssa Caddyn alla.

### 7.2 Henkilötietojen suodatus

Mestarin system instructions kieltävät henkilötietojen käytön (luku 5.3). Lisävarmistuksena Prototype API:ssa voidaan tehdä **kevyt regex-suodatus** käyttäjän inputiin: jos input sisältää ilmeisen henkilönimen, sähköpostiosoitteen tai puhelinnumeron, se anonymisoidaan ennen Mestarille lähettämistä.

Pilotissa tämä on hyvä lisätä mutta ei kriittinen — pääpaino on system instructionseissa.

### 7.3 Sandbox-eristys

Code Execution -sandbox on Googlen hallinnoima eristetty ympäristö joka ei pääse internettiin (paitsi Googlen sallimien rajapintojen kautta). Tämä on hyvä turvallisuusominaisuus: vaikka Mestari yrittäisi tehdä jotain odottamatonta, sandbox estää sen.

### 7.4 Lokitus

Kaikki palvelut lokittavat:
- Aikaleima
- Endpoint
- HTTP-status
- Latenssi millisekunteina
- Sandbox ID (jos relevantti)

**Ei lokiteta**:
- Käyttäjän inputtia
- Mestarin outputtia
- Konseptin tai raportin sisältöä
- STT-litterointia

Tämä on linjassa Reveal Engine -periaatteen kanssa.

---

## 8. Vaiheistus

B-dokumentin toteutus jakautuu kolmeen vaiheeseen jotka voidaan tehdä peräkkäin, kukin oma Codex-tehtävänä.

### Vaihe B1: Vertex AI Agent Engine + Prototype API

**Tavoite:** Toimiva sandbox-pohjainen Mestari joka osaa luoda ensimmäisen prototyypin konseptista ja iteroida sitä Koodaus-/Pohdinta-tiloissa.

**Tehtävät:**
1. Luo `kipina-vibe` Service Account, JSON-avain palvelimelle
2. Luo Vertex AI Agent Engine -instanssi `us-central1`-alueelle
3. Toteuta `apps/prototype-api/` (app.py, mestari.py, agent_engine.py, sandbox_state.py)
4. Kirjoita system instructions luvun 5 mukaisesti
5. Lisää docker-compose, Caddyfile-reititys
6. Smoke test: `curl POST /api/prototype/start` palauttaa toimivan HTML:n

**Riippuvuudet:** Concept API:n on toimittava (annetaan input).

### Vaihe B2: Template Proxy + Template Library

**Tavoite:** Mestari saa kutsua ulkoisia tietolähteitä proxyn kautta.

**Tehtävät:**
1. Toteuta `apps/template-proxy/` ja 13 templatea
2. Luo `templates.json` (sama tiedosto käytössä Prototype API:lla)
3. Päivitä Prototype API:n system instructions sisältämään Template Library -kuvaus
4. Lisää rate limiting per sandbox
5. Smoke test: kutsu jokaista templatea suoraan curlilla, varmista että vastaukset noudattavat skeemaa

**Riippuvuudet:** B1 valmis (Mestari osaa käyttää templateja).

### Vaihe B3: STT Proxy

**Tavoite:** Mikkinappula frontendissä toimii — ääni → teksti → Mestarille.

**Tehtävät:**
1. Toteuta `apps/stt-proxy/`
2. Smoke test: lähetä webm-ääninäyte curlilla, varmista litterointi
3. Päivitä Caddyfile

**Riippuvuudet:** Itsenäinen — voidaan tehdä rinnakkain B2:n kanssa.

---

## 9. Acceptance criteria koko B-vaiheelle

B on valmis kun KAIKKI alla olevat ovat tosia:

1. `docker compose build` rakentaa kaikki kolme uutta palvelua ilman virheitä
2. `docker compose up -d` käynnistää kaikki kolme palvelua
3. `docker ps` näyttää neljä Kipinä-palvelua terveinä (frontend, reveal-proxy, concept-api, prototype-api, stt-proxy, template-proxy)
4. Kaikki kolme uutta `/health`-endpointtia palauttavat 200 OK
5. `curl POST /api/prototype/start` konseptilla palauttaa toimivan HTML:n jossa on Tailwind-tyylit
6. `curl POST /api/prototype/iterate` Koodaus-tilassa palauttaa muokatun HTML:n
7. `curl POST /api/prototype/iterate` Pohdinta-tilassa palauttaa pelkän tekstin ilman HTML:ää
8. `curl /api/templates/weather-current?place=Helsinki` palauttaa säätiedon
9. Vähintään 10 templatea palauttavat odotetun rakenteen (3 maksullisen kanssa testataan saldon mukaan)
10. `curl POST /api/stt/transcribe` testitiedostolla palauttaa litteroidun tekstin
11. `curl POST /api/prototype/undo` palauttaa edellisen HTML-version sandboxin historiasta
12. Caddy-reitit toimivat publicista (`https://pilot.kipina.digiter.fi/api/prototype/health` jne.)
13. Vanhat reitit (`/api/concepts/*`, `/api/health`) toimivat edelleen
14. `secrets/gcp-sa-vibe.json` on palvelimella, gitignored, mounted read-only

---

## 10. Päätetyt asiat ja avoimet kysymykset

### 10.1 Päätetty

- **Undo-mekanismi**: Pilotissa in-memory versiohistoria Prototype API:n muistissa, max 20 askelta per sandbox. Ei GCS:ää tässä vaiheessa. API-pinta (`/undo`-endpoint) suunniteltu siten että toteutus voidaan myöhemmin siirtää GCS:ään ilman frontend-muutoksia.

### 10.2 Avoimet kysymykset

Nämä on hyvä päättää ennen kuin Codex aloittaa toteutuksen:

1. **Iteraatiohistorian tiivistys** — tehdäänkö pilotissa, vai säilytetäänkö koko historia kunnes sandbox päättyy? Pilottivolyymeillä koko historia mahtuu hyvin Geminin kontekstiin (1M tokenia).
2. **Concept drift -ilmoituksen toistuvuus** — onko enintään 1 kertaa istuntoa kohti riittävä rajoitus, vai pitäisikö olla esim. 1 kertaa per 10 iteraatiota?
3. **Mock-datan determinismi** — tehdäänkö mock-data deterministiseksi (sama vastaus joka kerta) vai pseudo-satunnaiseksi (vaihtelee mutta uskottavasti)?
4. **Translate-templaten kustannuskatto** — mikä on sopiva raja per sandbox? Ehdotus: 5000 merkkiä per sandbox koko session aikana.
5. **Sandbox-tilan persistenssi** — pidetäänkö se in-memory Python-dictionarynä (yksinkertainen, häviää restartissa) vai tallennetaanko levylle (vähän monimutkaisempi)? Pilotissa: in-memory.

---

## 11. Liitteet ja viittaukset

- A-dokumentti: `kipina-vibe-A-konsepti.md`
- Concept API: `concept-api-implementation.md`
- Caddy nykytila: `infra/caddy/Caddyfile`
- Reveal Engine: GitHub `reveal-api-kanavana`
- GCP-projekti: `apply-project-35406`
- Krediitit pilotille: 855€

---

*Loppu B-dokumentista. Seuraavaksi C (frontend).*
