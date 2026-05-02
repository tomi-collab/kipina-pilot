# Kipinä-pilotin tenant-luontiohje

Tämä dokumentti kuvaa, miten Kipinä-pilotin Reveal-tenantit rakennetaan 
Reveal Platformiin. Pohjautuu ensimmäisen tenantin (Mä ja maailma) 
toteutukseen ja päästä päähän -testiin, joka onnistui.

## Lähtötilanne

Kipinä-pilotissa on viisi tenanttia, jotka vastaavat eri suhdetasoja 
nuoren elämässä:

| Tenant id | Nuorelle näkyvä nimi | Mitä käsitellään |
|-----------|---------------------|------------------|
| `mina` | Mä itse | Nuoren oma sisäinen kokemus, omat tarpeet |
| `mina-ja-toinen` | Mä ja joku toinen | Kahdenväliset suhteet |
| `porukka` | Mä ja porukka | Lähiyhteisöt (koulu, harrastus, kaverit) |
| `maailma` | Mä ja maailma | Yhteiskunta, järjestelmät, instituutiot |
| `emma-tiia` | Emmä tiiä | Strukturoimaton lähtökohta |

Tenant id (= tenant_key) on URL-ystävällinen tunniste joka näkyy 
KIPINA_TENANTS-env-muuttujassa ja Kipinän URL-osoitteessa 
(`/idea/$tenant`). Sen on täsmättävä Reveal Platformin Tenant key 
-kentän kanssa.

## Reveal Platformin välilehdet ja niiden vastuualueet

Tenantilla on Reveal Platformissa seuraavat välilehdet:

1. **Settings** — metatiedot, milestonet, kielet, vuorojen määrä
2. **Guidance Layers** — kuusi kerrosta, jotka ohjaavat keskustelua
3. **Report Schema** — raportin lopullinen rakenne
4. **Data Policy** — anonymisointi, käytetään oletuksia
5. **API keys** — tenant_key + api_key (tarvitaan Kipinän .env-tiedostoon)
6. **Reports** — historiallinen näkymä, ei muokattavaa
7. **Audit** — historiallinen näkymä, ei muokattavaa

## Vastuualuejako: jaettu vs. tenanttispesifinen sisältö

Tämä on tärkein periaate. Kun teet uuden tenantin, älä kirjoita kaikkia 
kerroksia uudestaan — kopioi jaetut, muokkaa tenanttispesifiset.

| Sisältö | Jaettu vai tenanttispesifinen | Huomiot |
|---------|-------------------------------|---------|
| Conversation style | **Jaettu kaikille viidelle** | Sama nuorten puhuttelu kaikissa tenanteissa |
| Core rules | **Jaettu kaikille viidelle** | Ei viittaa tenantin aiheeseen |
| Report Schema (rakenne) | **Lähes jaettu** | 5 osiota samat, vain "Idean ydin" -osion sisältö muotoilussa viittaa tenantin aiheeseen |
| Settings (Role, Tone, Audience) | Pohja jaettu | Mukautetaan tenantin aiheeseen |
| Settings (Analysis level, Milestones, Max turns) | Tenanttispesifinen | Suhdetaso määrää valinnan |
| Tenant purpose | **Tenanttispesifinen** | Kuvaa mihin juuri tämä keskustelu on olemassa |
| Editable guidance | **Tenanttispesifinen** | Kuvaa tenantin oman keskustelutaktiikan |
| Safety boundaries | Pohja jaettu, lisäykset spesifisiä | Maailma: politiikka. Mä itse: mielenterveys. Mä ja toinen: lähisuhdeväkivalta. Porukka: kiusaaminen, syrjintä |
| Report instructions | **Tenanttispesifinen** | Painotuksen ohjaus, raportin sävy |

## Periaatteet sisällön kirjoittamiseen

Nämä on opittu Mä ja maailma -tenantin testaamisesta. Pidä mielessä 
kaikissa tenanteissa.

### 1. Kielimallille kirjoittaminen

- **Älä mainitse "Reveal", "tenantti", "kerros"** — kielimalli ei tiedä 
  niitä eikä niistä ole hyötyä. Kirjoita suoraan toimintaohjeena: 
  "Toimi näin", "Älä tee näin", "Kysy seuraavasti".
- **Käytä imperatiiveja** Editable guidance, Safety boundaries ja 
  Core rules -kerroksissa.
- **Käytä toteavaa tyyliä** Tenant purpose -kerroksessa ("Tämä keskustelu 
  on tarkoitettu...", "Keskustelun tehtävä on...").

### 2. Käyttäjän puhuttelu

- Käytä **"nuori"** kun konteksti sallii, ei "käyttäjä".
- Pidä yhdenmukaista terminologiaa kaikissa tenantin kerroksissa.

### 3. Päällekkäisyys kerrosten välillä

- **Tärkeät säännöt saavat olla useassa kerroksessa.** LLM huomaa ne 
  paremmin. Esim. kysymysrytmi voi olla sekä Conversation stylessa 
  että Core rulesissa.
- **Mutta:** jokaisen kerroksen pitäisi vastata yhdestä ydinasiasta. 
  Jos koko sisältö toistuu toisessa kerroksessa, se on virhe.

### 4. Pituus

- 200–400 sanaa per kerros on yleensä riittävä.
- Pitkä ja sekava on huonompi kuin lyhyt ja täsmällinen.

## Mä ja maailma -tenantin sisällöt referenssinä

### Settings

- Role: "Ideafasilitaattori, joka auttaa nuoria sanoittamaan ideoitaan 
  omasta suhteestaan yhteiskuntaan, instituutioihin ja laajempiin 
  järjestelmiin"
- Tone: "Lämmin, utelias, selkokielinen; ottaa nuoren havainnot 
  tosissaan ilman poliittista värittämistä"
- Goal: "Auta nuorta liikkumaan henkilökohtaisen kokemuksen ja 
  rakenteellisen havainnon välillä, ja tuottaa selkeä, jäsennelty 
  konsepti hänen ideastaan"
- Analysis level: "Yksilö ja järjestelmä"
- Max turns: 6
- Default/Conversation/Report language: fi
- Milestones (yksi per rivi): havainto, järjestelmä, muutos, luonnos
- Auto delete handoff state: päällä
- Mermaid diagrams enabled: pois
- Strict anonymization: päällä

### Guidance Layers

Kerrokset luotu järjestyksessä: Editable guidance → Safety boundaries 
→ Report instructions → Conversation style → Tenant purpose → Core rules.

Sisällöt löytyvät Reveal Platformin omasta versiohistoriasta 
(jokaisen kerroksen "Create new version" -toiminto näyttää aiemmat 
versiot). Päästä päähän -testin jälkeen voimassa olevat versiot:

- Editable guidance: v3
- Safety boundaries: v2
- Report instructions: v1
- Conversation style: v2
- Tenant purpose: v2
- Core rules: v1

### Report Schema

5-osainen: Idean ydin, Käyttäjäkuvaus, Sovelluksen toiminnot, Muutos 
nykytilaan, Avoimet kysymykset. Mermaid diagrams: pois.

## Työnkulku uutta tenanttia luotaessa

1. **Reveal Platformissa**: Create tenant → täytä perustiedot 
   (Organisation: Aseman Lapset, Project: kipina-pilot, Name: nuorelle 
   näkyvä, Tenant key: tekninen id, Status: Active)
2. **Settings-välilehti**: täytä Role, Tone, Goal, Analysis level, 
   Max turns, kielet, Milestones, rastit. Save draft.
3. **Guidance Layers**:
   - Kopioi Conversation style -sisältö Mä ja maailma -tenantilta 
     (jaettu)
   - Kopioi Core rules -sisältö Mä ja maailma -tenantilta (jaettu)
   - Kirjoita Tenant purpose tenantille (tenanttispesifinen)
   - Kirjoita Editable guidance tenantille (tenanttispesifinen)
   - Kirjoita Safety boundaries: pohja jaettu + tenanttikohtaiset 
     lisäykset
   - Kirjoita Report instructions tenantille (tenanttispesifinen)
   - Publish jokainen
4. **Report Schema**: kopioi Mä ja maailma -tenantilta, muokkaa 
   "Suhde järjestelmään" -kohta (jos viittaus aiheeseen) tenantin 
   aiheen mukaiseksi. Publish.
5. **API keys**: kopioi tenant_key ja api_key talteen
6. **Päivitä Kipinän .env**: vaihda KIPINA_TENANTS-arvossa kyseisen 
   tenantin tenant_key ja api_key PLACEHOLDER-arvosta oikeisiin
7. **Restart**: docker compose restart kipina-reveal-data-api
8. **Smoke test**: curl http://localhost:8081/api/health → tenant_count 
   pysyy 5
9. **Selaintest**: avaa Kipinä, kirjaudu, valitse uusi tenantti, 
   käy yksi keskustelu loppuun
10. **Iteroi** havaintojen pohjalta — Reveal Platformin Create new 
    version -toiminto antaa Villelle mahdollisuuden säätää kerroksia 
    ilman että vanhat keskustelut häiriintyvät

## Mitä testaamisessa havainnoidaan

- **Conversation style**: Aloittaako Reveal vuoroja kohteliaisuusfraaseilla? 
  Pidetäänkö vuorot lyhyinä?
- **Editable guidance**: Liikkuuko keskustelu tenantin aiheelle olennaisten 
  tasojen välillä? Jämähtääkö johonkin?
- **Core rules**: Pysyykö nuoren omissa sanoissa, ei keksi?
- **Settings + milestonet**: Eteneekö keskustelu järjestyksessä? Päättyykö 
  Max turns -rajaan finished: true -tilassa?
- **Report Schema**: Ovatko osiot oikeassa järjestyksessä ja sisältö 
  ohjeistetussa muodossa?

## Tunnetut iteraatiokohdat (Mä ja maailma -testin pohjalta)

- **Aloitusvuoron kohteliaisuusfraasit**: Reveal lipsahti yhden kerran 
  ("Kiitos, että jaoit tämän"), Conversation style v2 lisäsi 
  eksplisiittisen kiellon aloitusvuorolle.
- **Eteenpäin viemisen voima**: Reveal viipyi nykytilan kartoittamisessa, 
  Editable guidance v3 lisäsi ohjeen jatkaa eteenpäin kun konkreettinen 
  idea on annettu.

## Yhteenveto

Mä ja maailma -tenantti tuotti onnistuneen testikeskustelun, joka 
päättyi Selkis-konseptiin (Kelan virkakieltä avaava chat-sovellus 
nuorille). Polku Kipinän etusivulta keskustelun kautta raporttiin ja 
konseptiin toimii päästä päähän. Kerrosrakenne kestää, 
tutkimusasetelma pysyy puhtaana, ja Villellä on nyt iteraatiopohja.