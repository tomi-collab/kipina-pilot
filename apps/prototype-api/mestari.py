from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from google import genai
from google.genai import types


GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "europe-west4")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
TEMPLATE_PROXY_BASE_URL = os.environ.get("TEMPLATE_PROXY_BASE_URL", "http://template-proxy:8080").rstrip("/")
TEMPLATES_PATH = os.environ.get("TEMPLATES_PATH", "/app/templates.json")
MAX_HTML_CHARS = 50_000
MAX_TOOL_ROUNDS = 4
TOOL_TIMEOUT_SECONDS = 12

_client: genai.Client | None = None
_templates_metadata: dict[str, Any] | None = None


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

ITERATE_SCHEMA = {
    "type": "object",
    "properties": {
        "prototype_html": {"type": "string", "nullable": True},
        "mestari_message": {"type": "string"},
        "concept_drift_warning": {"type": "string", "nullable": True},
    },
    "required": ["mestari_message"],
}

TEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "mestari_message": {"type": "string"},
    },
    "required": ["mestari_message"],
}

ITERATE_INTENT_INSTRUCTION = """
NUOREN VIESTIN TULKINTA ITEROINNISSA:

Nuori kirjoittaa sinulle yhteen kenttään. Viesti voi olla:

1. MUUTOSPYYNTÖ — nuori haluaa että muutat sovellusta.
   Esim. "tee napista isompi", "lisää kohta jossa näkyy paikka",
   "vaihda väri", "poista toi osio". Tällöin: tuota uusi, päivitetty
   prototype_html ja kerro lyhyesti mitä muutit.

2. KYSYMYS TAI POHDINTA — nuori kysyy, ihmettelee tai miettii ääneen.
   Esim. "miksei tää toimi", "eiks sen pitäis näyttää X", "mitä mieltä
   oot", "en tajua miten tää menee". Tällöin: vastaa kysymykseen
   selkeästi ja lyhyesti. ÄLÄ tuota uutta prototype_html:ää — jätä se
   tyhjäksi (null). Älä keksi turhaa muutosta.
   Tärkeää: pelkkä kysymys tai ihmettely EI ole muutospyyntö, vaikka siinä
   lukisi "pitäis näyttää", "miksei näy" tai "eiks se tee". Vastaa mitä
   nykyinen prototyyppi tekee tai miten sitä voisi muuttaa. Älä muuta HTML:ää
   ilman selkeää pyyntöä kuten "lisää", "tee", "muuta", "vaihda", "poista",
   "näytä" tai "korjaa".

3. MOLEMPIA — viestissä on sekä muutospyyntö että kysymys.
   Esim. "tee nappi isommaks ja muuten miks toi teksti on tossa".
   Tällöin: tee muutos (tuota uusi prototype_html) JA vastaa
   kysymykseen mestari_message-kentässä.

PÄÄTÄ itse kumpi tai mikä viesti on. Älä kysy nuorelta "haluatko että
muutan vai vastaanko" — tulkitse suoraan. Jos olet epävarma, käsittele viesti
kysymyksenä/pohdintana ja palauta prototype_html: null.
"""

MESTARI_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_weather",
                description=(
                    "Hae nykyinen säätila suomalaiselle paikkakunnalle. "
                    "Kutsu tätä kun haluat nähdä millaista säädataa on saatavilla "
                    "ennen kuin rakennat sääsovelluksen UI:n."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "place": types.Schema(
                            type="STRING",
                            description="Paikkakunta suomeksi, esim. 'Helsinki'",
                        )
                    },
                    required=["place"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_transit",
                description=(
                    "Hae seuraavat joukkoliikenteen lähdöt Helsingin seudun pysäkiltä. "
                    "Kutsu tätä nähdäksesi lähtödatan rakenteen."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "stop_name": types.Schema(
                            type="STRING",
                            description="Pysäkin nimi, esim. 'Rautatientori'",
                        )
                    },
                    required=["stop_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="analyze_options",
                description=(
                    "Analysoi käyttäjän vaihtoehtoja (plussat/miinukset, järjestys, "
                    "suositus tai yhteenveto). Kutsu nähdäksesi analyysin muodon."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "question": types.Schema(type="STRING"),
                        "options": types.Schema(type="ARRAY", items=types.Schema(type="STRING")),
                        "analysis_type": types.Schema(
                            type="STRING",
                            description="pros_cons | ranking | advice | summary",
                        ),
                    },
                    required=["question", "options", "analysis_type"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_image",
                description=(
                    "Hae satunnaisen valokuvan URL prototyyppiin. Anna seed-merkkijono "
                    "(esim. aihe), niin saat saman kuvan joka kerta samalle seedille. "
                    "HUOM: kuvan SISÄLTÖ ei liity seediin — se on satunnainen valokuva. "
                    "Älä lupaa nuorelle tietynaiheista kuvaa."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "seed": types.Schema(
                            type="STRING",
                            description="Mikä tahansa merkkijono, esim. 'saasovellus'",
                        ),
                        "width": types.Schema(type="INTEGER"),
                        "height": types.Schema(type="INTEGER"),
                    },
                    required=["seed"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_calendar",
                description=(
                    "Hae esimerkki-viikkokalenteri (demo-dataa) sovelluksiin jotka "
                    "käsittelevät käyttäjän aikataulua. Data on keksittyä mutta uskottavaa."
                ),
                parameters=types.Schema(type="OBJECT", properties={}, required=[]),
            ),
            types.FunctionDeclaration(
                name="get_messages",
                description=(
                    "Hae esimerkki-viestiketju (demo-dataa) chat- tai viestisovellusten "
                    "prototyyppiin. Data on keksittyä, turvallista ja nuorille sopivaa."
                ),
                parameters=types.Schema(type="OBJECT", properties={}, required=[]),
            ),
            types.FunctionDeclaration(
                name="use_text_helper",
                description=(
                    "Käsittele tekstiä tekoälyllä: käännä, tiivistä, selkokielistä tai "
                    "muotoile. Käytä esim. kun globaali sisältö pitää kääntää nuorelle "
                    "suomeksi, tai pitkä teksti tiivistää."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "task": types.Schema(
                            type="STRING",
                            description="translate | summarize | simplify | rephrase",
                        ),
                        "text": types.Schema(type="STRING"),
                        "target_lang": types.Schema(
                            type="STRING",
                            description="fi | en | sv (vain translate)",
                        ),
                    },
                    required=["task", "text"],
                ),
            ),
        ]
    )
]


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


def _get_templates_metadata() -> dict[str, Any]:
    global _templates_metadata
    if _templates_metadata is None:
        try:
            with open(TEMPLATES_PATH, encoding="utf-8") as file:
                data = json.load(file)
        except OSError as exc:
            raise MestariError(f"templates metadata missing: {TEMPLATES_PATH}") from exc
        templates = data.get("templates")
        if not isinstance(templates, list):
            raise MestariError("templates metadata must include a templates list")
        _templates_metadata = data
    return _templates_metadata


def _template_by_id() -> dict[str, dict[str, Any]]:
    data = _get_templates_metadata()
    return {
        item["id"]: item
        for item in data["templates"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _selected_templates_section(suggested_templates: list[str] | None) -> str:
    if not suggested_templates:
        return ""
    templates = _template_by_id()
    rows = []
    for template_id in suggested_templates:
        item = templates.get(template_id)
        if item:
            rows.append(f"- {template_id}: {item.get('kuvaus', '')}")
    if not rows:
        return ""
    return """
TÄHÄN IDEAAN VALITUT TIETOLÄHTEET:

Konseptoinnissa on jo arvioitu, että tämä idea hyötyy erityisesti näistä
tietolähteistä:

{rows}

Käytä ensisijaisesti näitä. Voit käyttää muitakin jos idea selvästi sitä
vaatii, mutta älä pakota mukaan lähteitä joita ei tarvita.
""".format(rows="\n".join(rows))


def _build_template_library_section(sandbox_id: str = "", suggested_templates: list[str] | None = None) -> str:
    if not sandbox_id:
        return ""
    selected_section = _selected_templates_section(suggested_templates)
    return f"""
KÄYTETTÄVISSÄ OLEVAT TIETOLÄHTEET

{selected_section}

Sinulla on pääsy seitsemään tietolähteeseen, joita voit kutsua kahdella tavalla.

1. SÄÄ — get_weather(place): nykyinen säätila suomalaiselle paikkakunnalle
   (lämpötila, tuuli, kosteus).
2. JOUKKOLIIKENNE — get_transit(stop_name): seuraavat lähdöt Helsingin
   seudun pysäkiltä.
3. ANALYYSI — analyze_options(question, options, analysis_type): tekee
   vaihtoehdoista plussat/miinukset, järjestyksen, suosituksen tai
   yhteenvedon.

LISÄÄ TIETOLÄHTEITÄ:

4. KUVA — get_image(seed): satunnaisen valokuvan URL. Sama seed → sama
   kuva. Kuvan sisältö on satunnainen, ei liity seediin. Käytä elävöittämään
   ulkoasua, älä lupaa nuorelle tietynaiheista kuvaa.
5. KALENTERI (demo) — get_calendar(): esimerkki-viikko-ohjelma. Käytä kun
   idea käsittelee aikataulua tai viikon suunnittelua.
6. VIESTIT (demo) — get_messages(): esimerkki-viestiketju. Käytä chat- tai
   viestisovellusten demoksi.
7. TEKSTI — use_text_helper(task, text, target_lang): käännä, tiivistä,
   selkokielistä tai muotoile tekstiä. Käytä kun idea tarvitsee
   tekstinkäsittelyä tai esimerkiksi globaalia sisältöä suomeksi.

KAHDENLAISTA TYÖKALUJEN KÄYTTÖÄ:

1. KUN RAKENNAT TAI MUUTAT sovellusta: keskity niihin tietolähteisiin
   jotka tähän ideaan on valittu. Älä änkeä mukaan kaikkea — pidä
   sovellus selkeänä ja idean mukaisena.

2. KUN NUORI KYSYY MITÄ VOISI LISÄTÄ, esimerkiksi "voisiko tähän lisätä
   jotain", "mitä muuta tähän sopisi" tai "onko ideoita": harkitse KAIKKIA
   käytettävissä olevia tietolähteitä, älä vain niitä jotka jo ovat
   käytössä. Tämä on luova hetki — avaa nuorelle mahdollisuuksia.

   Käy mielessäsi läpi koko valikoima ja ehdota niitä jotka voisivat
   aidosti sopia juuri tähän ideaan:
   - Sää (get_weather), Joukkoliikenne (get_transit)
   - Analyysi/vertailu (analyze_options)
   - Kuvat (get_image), Kalenteri (get_calendar), Viestit (get_messages)
   - Tekstin käännös/tiivistys/selkokielistys (use_text_helper)
   - Kartta (Leaflet)

   Ehdota 2-4 konkreettista, tähän ideaan sopivaa lisäystä. Älä luettele
   kaikkia mekaanisesti, vaan valitse osuvimmat ja kerro lyhyesti miten
   kukin sopisi. Jos jokin tietolähde ei sovi ideaan, jätä se pois.

KAKSI TAPAA KÄYTTÄÄ NÄITÄ:

A) Suunnitellessasi: kutsu tietolähdettä NYT nähdäksesi millaista dataa
   se palauttaa, ja rakenna prototyypin ulkoasu sen todellisen rakenteen
   ympärille. Älä arvaa datan muotoa.

   Jos konsepti liittyy selvästi säähän, joukkoliikenteeseen, kuvalliseen
   sisältöön, kalenteriin/aikatauluun/viikkosuunnitteluun tai viesteihin,
   kutsu vastaavaa tietolähdettä suunnittelussa ennen lopullista HTML:ää.

B) Prototyypin sisällä: kirjoita prototyypin JavaScriptiin hakukutsu,
   joka hakee datan kun nuori avaa sovelluksen, jotta sovellus näyttää
   tuoretta tietoa. Käytä TÄSMÄLLEEN näitä osoitteita ja vain näitä:

   - Sää:           /api/templates/weather-current?place=PAIKKA
   - Joukkoliikenne: /api/templates/transit-helsinki?stop_name=PYSAKKI
   - Analyysi:       POST /api/templates/analyze  (JSON body)
   - Kuva:          /api/templates/image-random?seed=AIHE&width=600&height=400
   - Kalenteri:     /api/templates/calendar-mock
   - Viestit:       /api/templates/messages-mock
   - Teksti:        POST /api/templates/text-helper  (JSON body)

   Kuva voi mennä suoraan <img src>-tagiin (image_url-kentästä) ilman
   erillistä hakua, koska kuva on julkinen.

   Lisää jokaiseen hakuun header "X-Kipina-Sandbox-Id" arvolla joka on
   tässä: {sandbox_id}. Ilman sitä haku ei toimi.

TIETOLÄHTEIDEN HAKU PROTOTYYPISSÄ — TÄRKEÄ:

Kun haet dataa tietolähteistä prototyypin koodissa, kirjoita haku aina niin
että se kestää virheen. Verkko voi pätkiä ja vastaus voi epäonnistua. Älä
koskaan oleta että data tulee aina. Käytä tätä mallia:

  try {{
    const res = await fetch('/api/templates/...', {{
      headers: {{ 'X-Kipina-Sandbox-Id': '{sandbox_id}' }}
    }});
    if (!res.ok) throw new Error('haku epäonnistui');
    const data = await res.json();
    // käytä dataa tässä, tarkista että kentät ovat olemassa
    if (data && data.result) {{ /* näytä data */ }}
  }} catch (e) {{
    // näytä käyttäjälle ystävällinen viesti, ÄLÄ kaada sovellusta
    // esim. näytä "Tietoja ei juuri nyt saatu, yritä hetken kuluttua"
  }}

SÄÄNNÖT:
- Tarkista AINA res.ok ennen kuin luet vastausta.
- Tarkista AINA että odotettu kenttä on olemassa ennen kuin käytät sitä
  (esim. ennen .split(), .map(), .length).
- Näytä virhetilanteessa lyhyt ystävällinen viesti DOM:iin. Älä nojaa
  alert():iin virheiden ainoana palautekanavana.
- Sovellus ei saa koskaan jäädä rikkinäiseen tilaan yhden epäonnistuneen
  haun takia.

KÄYTTÄJÄN SYÖTE JA VIESTIT PROTOTYYPISSÄ:

Kun prototyyppi tarvitsee käyttäjältä syötettä (esim. nimi, tehtävä,
valinta) tai näyttää viestin, käytä ENSISIJAISESTI sivulle rakennettuja
elementtejä:
- Syöte: <input>- tai <textarea>-kenttä ja nappi, ei prompt().
- Viesti tai vahvistus: näytä teksti sivun omassa elementissä
  (esim. <div>), ei alert():ia.
- Valinta kyllä/ei: kaksi nappia sivulla, ei confirm():ia.

Miksi: prototyyppiä käytetään puhelimella, ja sivulle rakennetut kentät
ja viestit näyttävät paremmilta ja toimivat luotettavammin kuin selaimen
omat ponnahdusikkunat.

Natiivit alert(), prompt() ja confirm() TOIMIVAT, mutta käytä niitä vain
jos sivulle rakennettu ratkaisu olisi kohtuuttoman monimutkainen. Suosi
aina sivun omia elementtejä.

PROTOTYYPIN TEKNISET RAJAT (iframe-ympäristö):

Prototyyppi ajetaan rajatussa ympäristössä. Nämä TOIMIVAT, käytä vapaasti:
- JavaScript, lomakkeet, painikkeet, syötekentät
- alert/confirm/prompt, mutta suosi sivun omia elementtejä kuten yllä
- Leikepöydälle kopiointi: navigator.clipboard.writeText
- Koko näyttö: fullscreen, esimerkiksi peleissä

Nämä EIVÄT toimi — ÄLÄ käytä:
- Uusien ikkunoiden tai välilehtien avaaminen: window.open tai target=_blank
  ulkoisille linkeille.
- Sivulta pois navigointi: window.top, window.parent tai parent.
- Leikepöydän LUKEMINEN: navigator.clipboard.readText.
- Kamera, mikrofoni tai sijainti.

ROBUSTIUS: vaikka ominaisuus on sallittu, se voi epäonnistua. Käsittele
aina siististi:
- Kopiointi: kääri try/catchiin. Näytä "Kopioitu!" vain jos kirjoitus
  onnistui. Jos kopiointi epäonnistuu, näytä teksti valittavana kenttänä
  tai elementtinä ja ohje "kopioi tästä".

  Esimerkki:
    try {{
      await navigator.clipboard.writeText(teksti);
      // näytä "Kopioitu!"
    }} catch (e) {{
      // näytä teksti valittavana + ohje "kopioi tästä"
    }}

- Älä koskaan jätä prototyyppiä rikkinäiseen tilaan jos jokin
  selainominaisuus estyy.

PROTOTYYPIN ILME — TEE SIITÄ NUOREN NÄKÖINEN:

Älä tee geneeristä, harmaata "ohjelmiston" näköistä sovellusta. Jokainen
prototyyppi saa oman luonteensa idean tunnelman mukaan. Valitse YKSI
seuraavista neljästä tyylisuunnasta sen perusteella, millainen idea on:

1. ENERGINEN — pelit, haasteet, kaveriporukan hauskat jutut, kilpailut.
   - Rohkeat, kirkkaat värit ja gradientit (esim. violetti→pinkki,
     syaani→sininen). Tumma tausta + hehkuvat aksentit toimii hyvin.
   - Isot, lihavat otsikot. Pyöreät, isot napit. Selkeää liikettä:
     hover-skaalaus, napsahdukset, kevyet animaatiot.
   - Tunnelma: innostava, leikkisä, "tää on hauskaa".

2. RAUHALLINEN — päiväkirja, fiiliksen seuranta, hyvinvointi, oma rauha.
   - Pehmeät, vaaleat sävyt (esim. lämmin beige, vaalea sininen, salvia).
     Paljon tyhjää tilaa, ilmava.
   - Pehmeät reunat, hienovarainen, ei räväkkä. Vähän tai ei liikettä.
   - Tunnelma: turvallinen, rauhoittava, henkilökohtainen.

3. SELKEÄ — työkalut, listat, suunnittelu, porukan organisointi.
   - Raikas mutta jäsennelty. Yksi vahva pääväri + neutraalit. Hyvä
     hierarkia, selkeät osiot, helppo silmäillä.
   - Toimiva ja tehokas, MUTTA EI tylsä — käytä yhtä erottuvaa väriä ja
     hyvää typografiaa tuomaan eloa.
   - Tunnelma: "tää on selkeä ja auttaa mua saamaan asiat järjestykseen".

4. ROHKEA — maailma-aiheet, vaikuttaminen, kantaaottavat ideat.
   - Vahva, julistemainen typografia. Voimakas kontrasti (esim. musta +
     yksi kirkas väri). Isot tekstit, vähän koristeita.
   - Tunnelma: "tällä on väliä", näkyvä ja vaikuttava.

VALINTA:
- Päättele idean tunnelmasta mikä suunta sopii. Älä kysy nuorelta.
- Jos idea on rajatapaus, valitse lähin sopiva.
- Käytä Google Fontsia (lataa CDN:stä) persoonalliseen typografiaan —
  älä tyydy oletusfontteihin. Valitse fontti joka sopii valittuun
  suuntaan.

KERRO NUORELLE: mainitse lyhyesti viestissäsi minkä tyylin valitsit ja
että sen voi vaihtaa. Esim. "Tein tästä energisen ja värikkään — sano jos
haluat eri tunnelman." Pidä maininta lyhyenä, älä selitä pitkästi.

JOS NUORI PYYTÄÄ ERI TYYLIÄ: kun nuori sanoo esim. "tee rauhallisempi",
"liian tylsä", "energisemmäksi", vaihda koko prototyypin ilme toiseen
suuntaan ja tuota uusi prototype_html. Tämä on muutospyyntö.

SAAVUTETTAVUUS — PIDÄ NÄMÄ KAIKISSA SUUNNISSA (ei neuvoteltavissa):
- Tekstin ja taustan kontrastin on oltava korkea ja helposti luettava
  (tavoittele AAA-tasoa). Rohkeat värit eivät saa heikentää luettavuutta.
- Kosketuskohteet (napit, linkit, valinnat) vähintään 48x48 pikseliä.
  Käytä esimerkiksi Tailwind-luokkia min-h-12, px-4 ja py-3.
- Lisää aina CSS-sääntö prefers-reduced-motionille. Jos käyttäjä on
  valinnut sen, poista tai vaimenna animaatiot ja siirtymät:
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
- Mobiili ensin: kaikki suunnat suunnitellaan pienelle näytölle.

KARTTA (jos idea tarvitsee karttaa):

Älä hae karttaa tietolähteistä. Lisää interaktiivinen kartta suoraan
prototyyppiin Leaflet-kirjastolla CDN:stä. Käytä tätä mallia:

  <link rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <div id="map" style="height: 300px;"></div>
  <script>
    const map = L.map('map').setView([60.1699, 24.9384], 13); // Helsinki
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19
    }}).addTo(map);
    L.marker([60.1699, 24.9384]).addTo(map);
  </script>

SÄÄNNÖT:
- Säilytä attribuutio "© OpenStreetMap contributors" aina — se on pakollinen.
- Vaihda koordinaatit ([lat, lon]) sen mukaan mihin idea liittyy.
- Pidä karttakäyttö kohtuullisena (yksi kartta per prototyyppi riittää).

SÄÄNNÖT:
- Käytä vain yllä lueteltuja tietolähteiden osoitteita. Älä hae muista data-API-osoitteista.
- Jos idea tarvitsee dataa jolle ei ole lähdettä, tee uskottava
  staattinen demo prototyypin sisään ja merkitse se selvästi: "Demo".
- Älä koskaan laita prototyyppiin oikeita henkilötietoja, salasanoja
  tai avaimia.
- Hae dataa vain jos konsepti sitä oikeasti tarvitsee. Jos idea ei liity
  säähän tai liikenteeseen, älä pakota niitä mukaan.
- Jos idea käsittelee viikkosuunnittelua tai aikatauluja, älä kovakoodaa
  kalenterimerkintöjä ensisijaiseksi dataksi, vaan hae ne calendar-mockista.
- Jos idea käsittelee viestejä tai chattia, älä kovakoodaa keskustelua
  ensisijaiseksi dataksi, vaan hae se messages-mockista.
- Jos idea käsittelee käännöstä, tiivistämistä, selkokielistämistä tai
  tekstin uudelleenmuotoilua, käytä text-helperiä.

LOPULLINEN VASTAUS:
Kun olet valmis, palauta pelkkä validi JSON-objekti ilman muuta tekstiä
tai koodiaitaa. Koodaus-tilassa muoto on:
{{"prototype_html":"...","mestari_message":"...","concept_drift_warning":null}}
"""


def _system_instruction(
    sandbox_id: str = "",
    suggested_templates: list[str] | None = None,
    extra_instruction: str = "",
) -> str:
    return "\n\n".join(
        part
        for part in [
            MESTARI_PERUSROOLI.strip(),
            MESTARI_TEHTAVAKUVA.strip(),
            _build_template_library_section(sandbox_id, suggested_templates).strip(),
            extra_instruction.strip(),
        ]
        if part
    )


def _language_instruction(language: str) -> str:
    if language == "en":
        return "Write mestari_message in English. Keep the prototype UI language consistent with the concept unless the user asks otherwise."
    return "Kirjoita mestari_message suomeksi. Pidä prototyypin käyttöliittymä konseptin kielellä, ellei käyttäjä pyydä muuta."


def _generate_json(prompt: str, schema: dict[str, Any], extra_system_instruction: str = "") -> dict[str, Any]:
    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_system_instruction(extra_instruction=extra_system_instruction),
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


def _part_from_function_response(name: str, response: dict[str, Any]) -> types.Part:
    factory = getattr(types.Part, "from_function_response", None)
    if callable(factory):
        return factory(name=name, response=response)
    return types.Part(function_response=types.FunctionResponse(name=name, response=response))


def _content(role: str, parts: list[types.Part]) -> types.Content:
    return types.Content(role=role, parts=parts)


def _extract_parts(response: Any) -> list[Any]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    return list(getattr(content, "parts", None) or [])


def _extract_text(response: Any) -> str:
    text = (getattr(response, "text", None) or "").strip()
    if text:
        return text
    pieces = []
    for part in _extract_parts(response):
        part_text = getattr(part, "text", None)
        if part_text:
            pieces.append(part_text)
    return "\n".join(pieces).strip()


def _function_calls(response: Any) -> list[Any]:
    calls = []
    for part in _extract_parts(response):
        function_call = getattr(part, "function_call", None)
        if function_call and getattr(function_call, "name", None):
            calls.append(function_call)
    return calls


def _function_args(function_call: Any) -> dict[str, Any]:
    args = getattr(function_call, "args", None)
    if isinstance(args, dict):
        return dict(args)
    try:
        return dict(args or {})
    except (TypeError, ValueError):
        return {}


def _request_json(method: str, url: str, sandbox_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"X-Kipina-Sandbox-Id": sandbox_id}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TOOL_TIMEOUT_SECONDS) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {"value": parsed}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            payload = {"error": "template_proxy_error", "detail": str(exc)}
        if isinstance(payload, dict):
            return payload
        return {"error": "template_proxy_error", "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"error": "template_proxy_error", "detail": str(exc)[:240]}


def _execute_tool(name: str, args: dict[str, Any], sandbox_id: str) -> dict[str, Any]:
    print(f"mestari tool_call={name}", flush=True)
    if name == "get_weather":
        place = str(args.get("place", "")).strip()
        query = urllib.parse.urlencode({"place": place})
        return _request_json("GET", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/weather-current?{query}", sandbox_id)
    if name == "get_transit":
        stop_name = str(args.get("stop_name", "")).strip()
        query = urllib.parse.urlencode({"stop_name": stop_name})
        return _request_json("GET", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/transit-helsinki?{query}", sandbox_id)
    if name == "analyze_options":
        options = args.get("options")
        if not isinstance(options, list):
            options = []
        body = {
            "question": str(args.get("question", "")).strip(),
            "options": [str(option) for option in options],
            "analysis_type": str(args.get("analysis_type", "")).strip(),
            "language": "fi",
        }
        return _request_json("POST", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/analyze", sandbox_id, body)
    if name == "get_image":
        query = urllib.parse.urlencode(
            {
                "seed": str(args.get("seed", "")).strip(),
                "width": args.get("width", 600),
                "height": args.get("height", 400),
            }
        )
        return _request_json("GET", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/image-random?{query}", sandbox_id)
    if name == "get_calendar":
        return _request_json("GET", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/calendar-mock", sandbox_id)
    if name == "get_messages":
        return _request_json("GET", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/messages-mock", sandbox_id)
    if name == "use_text_helper":
        body = {
            "task": str(args.get("task", "")).strip(),
            "text": str(args.get("text", "")).strip(),
            "target_lang": str(args.get("target_lang", "fi")).strip() or "fi",
        }
        return _request_json("POST", f"{TEMPLATE_PROXY_BASE_URL}/api/templates/text-helper", sandbox_id, body)
    return {"error": "unknown_tool", "detail": f"Unknown tool: {name}"}


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _parse_json_text(text: str) -> dict[str, Any]:
    candidate = _strip_json_fence(text)
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except ValueError as exc:
        raise MestariError("Gemini returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise MestariError("Gemini returned non-object JSON")
    return parsed


def _generate_json_with_tools(
    prompt: str,
    sandbox_id: str,
    suggested_templates: list[str] | None = None,
    extra_system_instruction: str = "",
) -> dict[str, Any]:
    client = _get_client()
    contents = [_content("user", [types.Part(text=prompt)])]
    config = types.GenerateContentConfig(
        system_instruction=_system_instruction(sandbox_id, suggested_templates, extra_system_instruction),
        tools=MESTARI_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.7,
    )

    response = None
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        calls = _function_calls(response)
        if not calls:
            break

        model_parts = _extract_parts(response)
        if model_parts:
            contents.append(_content("model", model_parts))
        response_parts = []
        for function_call in calls:
            name = str(function_call.name)
            result = _execute_tool(name, _function_args(function_call), sandbox_id)
            response_parts.append(_part_from_function_response(name, result))
        contents.append(_content("user", response_parts))
    else:
        contents.append(
            _content(
                "user",
                [types.Part(text="Jatka ilman lisätyökalukutsuja. Palauta vain validi JSON ilman muuta tekstiä.")],
            )
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction(sandbox_id, suggested_templates, extra_system_instruction),
                temperature=0.7,
            ),
        )

    text = _extract_text(response)
    if not text:
        contents.append(_content("user", [types.Part(text="Palauta nyt lopullinen validi JSON ilman muuta tekstiä.")]))
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction(sandbox_id, suggested_templates, extra_system_instruction),
                temperature=0.2,
            ),
        )
        text = _extract_text(response)
    if not text:
        raise MestariError("Gemini returned an empty response")
    try:
        return _parse_json_text(text)
    except MestariError:
        contents.append(_content("model", [types.Part(text=text)]))
        contents.append(_content("user", [types.Part(text="Palauta vain validi JSON ilman muuta tekstiä.")]))
        retry = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction(sandbox_id, suggested_templates, extra_system_instruction),
                temperature=0.2,
            ),
        )
        retry_text = _extract_text(retry)
        if not retry_text:
            raise MestariError("Gemini returned an empty response")
        return _parse_json_text(retry_text)


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


def create_initial_prototype(
    concept: str,
    report: str,
    language: str = "fi",
    sandbox_id: str = "",
    suggested_templates: list[str] | None = None,
) -> dict:
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
Palauta lopuksi vain JSON skeeman mukaisesti, ilman koodiaitaa tai selittävää tekstiä.

KONSEPTI:
---
{concept}
---

RAPORTTI:
---
{report}
---
"""
    data = (
        _generate_json_with_tools(prompt, sandbox_id, suggested_templates)
        if sandbox_id
        else _generate_json(prompt, CODE_SCHEMA)
    )
    return {
        "prototype_html": _validate_html(data.get("prototype_html")),
        "mestari_message": _message(data.get("mestari_message"), "Rakensin ensimmäisen version."),
        "concept_drift_warning": data.get("concept_drift_warning"),
    }


def _optional_prototype_html(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return _validate_html(value)


def iterate(
    current_html: str,
    recent_iterations: list[dict],
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi",
    sandbox_id: str = "",
    suggested_templates: list[str] | None = None,
) -> dict:
    prompt = f"""
TILA: ITEROINTI

Tehtävä: Tulkitse nuoren viesti ja joko muuta prototyyppiä, vastaa kysymykseen
tai tee molemmat.

{_language_instruction(language)}

Säännöt:
- Jos muutat prototyyppiä, palauta kokonainen uusi HTML-dokumentti, ei diffiä.
- Jos et muuta prototyyppiä, palauta prototype_html: null.
- Säilytä toimivat osat ellei nuori pyydä muuttamaan niitä.
- Jos käyttäjä antaa henkilötietoja, yleistät ne prototyypissä.
- Jos pyyntö vie selvästi kauas konseptista, täytä concept_drift_warning lyhyellä muistutuksella. Muuten null.
- Palauta lopuksi vain JSON ilman koodiaitaa tai selittävää tekstiä.
- JSON-muoto on:
  {{"prototype_html": "<kokonainen HTML jos muutit, muuten null>", "mestari_message": "...", "concept_drift_warning": null}}

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
    data = (
        _generate_json_with_tools(
            prompt,
            sandbox_id,
            suggested_templates,
            extra_system_instruction=ITERATE_INTENT_INSTRUCTION,
        )
        if sandbox_id
        else _generate_json(prompt, ITERATE_SCHEMA, extra_system_instruction=ITERATE_INTENT_INSTRUCTION)
    )
    warning = data.get("concept_drift_warning")
    if not isinstance(warning, str) or not warning.strip():
        warning = None
    prototype_html = _optional_prototype_html(data.get("prototype_html"))
    return {
        "prototype_html": prototype_html,
        "mestari_message": _message(data.get("mestari_message")),
        "concept_drift_warning": warning,
        "changed": prototype_html is not None,
    }


def iterate_koodaus(
    current_html: str,
    recent_iterations: list[dict],
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi",
    sandbox_id: str = "",
    suggested_templates: list[str] | None = None,
) -> dict:
    return iterate(
        current_html,
        recent_iterations,
        user_input,
        concept,
        report,
        language,
        sandbox_id,
        suggested_templates,
    )


def iterate_pohdinta(
    current_html: str,
    recent_iterations: list[dict],
    user_input: str,
    concept: str,
    report: str,
    language: str = "fi",
) -> dict:
    return iterate(current_html, recent_iterations, user_input, concept, report, language)
