# Kipinä Vibe — A. Konsepti

**Dokumentti:** A/3 (Konsepti)
**Päivätty:** 2026-05-28
**Kirjoittaja:** Tomi Turpeinen + Claude (suunnittelukeskustelu)
**Tila:** Luonnos kommentoitavaksi

---

## 1. Mistä tässä on kyse

Kipinässä on tällä hetkellä toimiva päästä päähän -putki ideakeskustelusta konseptiin: nuori käy Reveal-keskustelun, saa raportin, ja Concept API muotoilee raportista sovelluskonseptin. Putken viimeinen lenkki — konseptista toimivaan selainprototyyppiin — on placeholder.

Tämä dokumentti kuvaa, miten viimeinen lenkki suljetaan: rakennetaan **vibekoodausnäkymä**, jossa nuori voi puheen ja tekstin avulla iteroida prototyyppiä **Mestarin** kanssa kunnes selainprototyyppi vastaa konseptia.

Tavoite ei ole rakentaa Cursor-luokan kehitysympäristöä nuorelle. Tavoite on antaa nuorelle kokemus siitä, että **hänen idea muuttuu hänen silmiensä edessä toimivaksi sovellukseksi, jossa hän itse on ohjaksissa**. Kokemuksen pitää olla kevyt, palkitseva ja konseptiuskollinen.

---

## 2. Mestari — roolin ja persoonallisuuden perusta

Vibekoodausvaiheen tekoälyä ei kutsuta agentiksi, botiksi eikä avustajaksi. Sitä kutsutaan **Mestariksi**. Tämä on tarkoituksellinen designvalinta, jolla on käytännön seurauksia.

### Mestarin tehtävä

Mestari on käsityöläinen joka rakentaa nuoren idean näkyväksi. Hän ei ole opettaja, terapeutti eikä mentori. Hän ei pyri kasvattamaan eikä korjaamaan nuorta. Hänen ainoa työnsä on **tehdä idea näkyväksi** ja pitää huoli siitä, että idea pysyy nuoren omana.

### Mestarin äänensävy

Lämmin mutta ammattimainen. Ei imartele, ei käytä motivaatiopuhetta, ei aloita vuoroja kiitoksella tai validoinnilla (samat säännöt kuin Reveal-keskustelussa). Lyhyt ja toimiva. Mestari saa kommentoida työtä mutta ei selitä metodejaan pitkästi.

Hyvä Mestari-vuoro:
> "Vaihdetaan väri vihreäksi ja katsotaan miltä näyttää."

Huono Mestari-vuoro:
> "Hieno valinta! Vihreä on rauhoittava väri, joka sopii hyvin sovelluksen tunnelmaan. Olen samaa mieltä siitä, että..."

### Mestarin muisti ja konseptiuskollisuus

Mestari muistaa alkuperäisen konseptin koko vibekoodausistunnon ajan. Konsepti (Concept API:n tuottama kuvaus + alkuperäinen Reveal-raportti) on hänen työpiirustuksensa. Jos nuori alkaa eksyä sivupoluille ("vaihdetaanpa kokonaan toiseen aiheeseen"), Mestari **muistuttaa hellävaraisesti** alkuperäisestä ideasta — ei estä, mutta ei myöskään seuraa hiljaa.

Rautalangassa tämä näkyy esimerkkinä:
> "Mestari huomauttaa: Olet rakentamassa hienoa juttua. Pidetäänkö kiinni siitä alkuperäisestä sääsovellus-ideasta?"

Tämä on suora yhteys Reveal-keskustelun ydinperiaatteeseen: nuoren oma sanoittaminen on kallisarvoista, ja kaikki rakennelmat sen päälle nojaavat siihen.

---

## 3. Kaksi tilaa — Koodaus ja Pohdinta

Mestarin kanssa työskennellessä on kaksi tilaa, jotka käyttäjä vaihtaa rautalangassa näkyvällä toggle-kytkimellä:

### Koodaus-tila (oletus, vihreä)

Käyttäjän puhe tai teksti tulkitaan **muutospyyntönä prototyyppiin**. Mestari tekee muutoksen sandboxissa ja päivittää iframessa näkyvän prototyypin. Tämä on tila jota käytetään suurimman osan ajasta.

Esimerkkejä Koodaus-tilan vuoroista:
- "Tee tästä neonvihreä."
- "Lisää nappi joka näyttää säätilan."
- "Mobiilioptimoitu."
- "Vaihda kellonaika isommaksi."

### Pohdinta-tila (sininen)

Käyttäjän puhe tai teksti tulkitaan **keskusteluksi konseptista, ei muutospyynnöksi**. Mestari ei tee koodimuutoksia, vaan keskustelee. Tila on tarkoitettu hetkiin jolloin nuori ei tiedä mitä tekisi seuraavaksi, haluaa miettiä suuntaa ääneen tai tarvitsee taustaa jollekin päätökselleen.

Esimerkkejä Pohdinta-tilan vuoroista:
- "Miksi sä laitoit tuon napin tuonne?"
- "Mitä jos tää olis ihan eri sovellus?"
- "En tiedä mikä tässä on vikana."

Tilojen erottaminen on tärkeää, koska se antaa nuorelle **selkeän valinnan** siitä, mitä hän haluaa juuri nyt. Jos kaikki tulkittaisiin Koodaus-tilan kautta, jokainen "mitä mieltä oot" -tyyppinen kysymys johtaisi tarpeettomaan koodimuutokseen. Jos kaikki tulkittaisiin Pohdinta-tilan kautta, prototyyppi ei koskaan etenisi.

### Tilojen tekninen ero

Koodaus-tilassa Mestarin vastaus sisältää sandbox-suorituksen ja uuden iframe-päivityksen. Pohdinta-tilassa Mestarin vastaus on pelkkä teksti, joka näkyy keskusteluhistoriassa tai erillisessä Mestarin huomio -kentässä rautalangan mukaisesti.

---

## 4. Käyttäjäpolku konseptin jälkeen

Tämä jatkuu siitä mihin nykyinen Kipinä-frontend päättyy: konseptinäkymä on auki, Concept API on palauttanut konseptin, nuori on lukenut sen.

### Vaihe 1: Vibekoodaussession aloitus

Konseptinäkymässä on **"Aloita vibekoodaus"** -nappi (nykyinen "Tee prototyyppi" -placeholder korvataan tällä). Nappia painaessaan:

1. Frontend kutsuu Prototype API:a `POST /api/prototype/start` -endpointilla
2. Mukana lähetetään: konsepti, alkuperäinen Reveal-raportti, tenant-id, sessio-id
3. Prototype API luo Vertex AI Agent Engine -sandboxin (TTL 1h aluksi)
4. Mestari generoi **ensimmäisen prototyyppiversion** sandboxissa pelkän konseptin pohjalta
5. Frontend siirtyy vibekoodausnäkymään ja näyttää ensimmäisen version iframessa

Tämä alkuvaihe on tärkeä: nuori näkee heti jotain konkreettista, ei tyhjää canvasia. Mestari on tehnyt ensimmäisen luonnoksen jo valmiiksi.

### Vaihe 2: Iteraatio

Vibekoodausnäkymässä nuori voi:

- Pitää mikkinappulaa pohjassa ja **puhua** muutostoiveen (STT muuntaa puheen tekstiksi tekstikenttään)
- **Kirjoittaa** muutostoiveen tekstikenttään suoraan
- Painaa **pikatoimintoa** ("Vaihda tyyliä", "Mobiilioptimoitu") joka täyttää tekstikentän valmiilla promptilla
- Vaihtaa **Koodaus/Pohdinta-tilaa** toggle-kytkimellä
- Painaa **Päivitys-nappia** lähettääkseen pyynnön Mestarille

Iteraatiokierros:
1. Nuori muotoilee pyynnön (puhuen tai kirjoittaen)
2. Painaa Päivitys
3. Frontend lähettää pyynnön Prototype API:lle
4. Mestari käsittelee pyynnön sandboxissa
5. Frontend päivittää iframen uudella versiolla (Koodaus-tila) tai näyttää Mestarin huomion (Pohdinta-tila)

### Vaihe 3: Session päättyminen

Sandbox elää tunnin verran (alkuvaiheessa). Session voi päättyä kahdella tavalla:

- **Aktiivinen lopetus**: Nuori sulkee näkymän tai siirtyy takaisin. Lopullinen versio voidaan tallentaa myöhempää tarkastelua varten (HTML-tiedostona tai linkkinä — yksityiskohdat B-dokumentissa).
- **Passiivinen päättyminen**: Sandbox TTL umpeutuu. Nuori voi aloittaa uuden vibekoodaussession samalla konseptilla, mutta aiempi iteraatiopolku katoaa.

Pilotissa ei rakenneta sessio-tilan pitkäaikaistallennusta. Tämä on rajoitus jonka voi avata myöhemmin.

---

## 5. Periaatteet jotka pitää säilyttää

Vibekoodausvaiheen pitää pysyä linjassa Kipinän koko muun toiminnan periaatteiden kanssa. Nämä on kirjattu, jotta system instructionsia ja teknisiä valintoja tehdessä ei ajauduta sivuun.

### 5.1 Nuoren oma idea on lähde

Mestari ei keksi nuoren puolesta. Jos prototyyppiin tarvitaan jotakin mistä nuori ei ole puhunut (esimerkiksi käyttöliittymän asettelua), Mestari käyttää konseptia perustana ja tekee minimaaliset valinnat itse — ei innovoi.

### 5.2 Ei henkilötietoja

Konsepti tulee Concept API:lta jo DLP-puhdistettuna, ja Reveal-raportissa noudatetaan anonymisointia. Mestari ei pyydä eikä käytä henkilötietoja prototyyppiin. Jos nuori syöttää nimensä tai muun henkilötiedon ("tee tästä Tomin sovellus"), Mestari **käyttää yleistä ilmaisua** ("käyttäjän sovellus") tai pyytää geneerisempää muotoa.

### 5.3 Ulkoiset tietolähteet vain Template Libraryn kautta

Prototyypin pitää toimia iframessa ilman suoria third-party -kutsuja, kirjautumisia tai paljaita API-avaimia. Mutta **prototyypin pitää myös tuntua eläväksi** — pelkkä staattinen kuvitus omasta ideasta ei riitä innostamaan nuorta. Sovelluksessa pitää tapahtua jotakin: säätiedot, joukkoliikenne, kuvat, sitaatit, kartat.

Ratkaisuna on **Kipinä API Template Library** (kuvattu luvussa 6.5), joka tarjoaa Mestarille rajatun joukon valmiita tietolähteitä Kipinän oman proxyn kautta. Mestari saa kutsua näitä iframen koodista, mutta ei muita ulkoisia osoitteita. Tämä pitää prototyypin elävänä, mutta turvallisena ja ennustettavana.

### 5.4 Yksitiedostoinen output (tai CDN-React)

Mestari tuottaa joko:
- Yksitiedostoisen HTML+CSS+JS:n joka toimii suoraan iframen `srcdoc`-attribuutissa
- React-prototyypin CDN-kirjastoilla ja Babel-standalonella (myös yksi tiedosto)

Ei npm-paketteja jotka vaativat asennusta selaimessa. Ei build-vaihetta. Code Execution -sandboxissa Mestari saa käyttää Pythonia ja Node.js:ää datan käsittelyyn ja kehitysapuna, mutta lopullinen output on aina selaimessa pyörivä yksi tiedosto.

### 5.5 Konseptiuskollisuus iteraatioissa

Mestarin pitää hellävaraisesti pitää nuori konseptin alueella. Jos nuori pyytää kymmenettä muutosta joka vie sovellusta yhä kauemmaksi alkuperäisestä ideasta, Mestari voi **kerran** muistuttaa ("Pidetäänkö kiinni alkuperäisestä?"). Jos nuori vahvistaa että hän haluaa todella vaihtaa suuntaa, Mestari seuraa — nuoren oma idea voittaa.

---

## 6. Mitä rakennetaan teknisesti

Tarkat tiedot B- ja C-dokumenteissa. Lyhyt yhteenveto:

### Uudet backend-palvelut

| Palvelu | Portti | Vastuu |
|---------|--------|--------|
| Prototype API | 8083 | Vertex AI Agent Engine -kutsut, sandbox-elinkaaren hallinta, system instructions |
| STT Proxy | 8084 | Google Cloud Speech-to-Text -kutsut, äänen välitys |

### Caddy-reititys

Lisätään `/api/prototype/*` ja `/api/stt/*` -reitit ennen olemassa olevia reittejä, samalla periaatteella kuin Concept API.

### Frontendin uusi näkymä

VibeStudioView (tai vastaava nimi) — sisältää:
- Iframe live preview (oikealla / pääalueella)
- Kontrollipaneeli (vasemmalla / alhaalla mobiilissa)
  - Prompt-tekstikenttä
  - Mikkinappula (push-to-talk)
  - Pikatoimintonapit
  - Koodaus/Pohdinta-toggle
  - Päivitys-nappi
- Mestarin huomio -kenttä (näkyy kun Mestari kommentoi tai muistuttaa)

### Vertex AI Agent Engine

Yksi Agent Engine -instanssi `apply-project-35406`-projektissa, `us-central1`-alueella (Code Execution vaatii tämän). Käyttäjäkohtaisia sandboxeja luodaan istunnoittain, TTL 1h aluksi.

---

## 6.5 API Template Library — sovellusinnostuksen ylläpitäjä

### Miksi tämä on välttämätön

Jos prototyyppi on vain staattinen kuvitus — napit, värit, layout — nuori näkee miltä sovellus voisi näyttää, mutta ei miltä se voisi **tuntua käytössä**. Staattinen "23°C" ei innosta. Säätieto joka päivittyy nuoren omalla paikkakunnalla tekee sovelluksesta eläväksi.

Kipinäputken oppimistavoite on, että nuori näkee idean **toimivana sovelluksena**, ei pelkkänä rautalankana. Tähän tarvitaan ulkoista dataa.

### Yhteys Concept API:hin

Concept API:n nykyinen prompt pyytää "Tarvittavat tietovirrat" -osiota, jossa LLM listaa **abstraktilla tasolla** millaista tietoa sovellus tarvitsisi: "reaaliaikaista joukkoliikenteen aikataulutietoa", "julkista säätietoa", "kuvantunnistusta valokuvasta". Tämä on tarkoituksellisesti kuvattu ilman palvelunimiä.

Vibekoodausvaiheessa nämä abstraktit tarpeet muunnetaan **konkreettisiksi API-kutsuiksi** Template Libraryn kautta. Konsepti ja templatekirjasto yhdessä antavat Mestarille selkeän rajan: hän tietää mitä saa kutsua ja miten.

### Kaksi tasoa

**Taso 1: Oikeat julkiset tietolähteet.** Sää, joukkoliikenne, kartat, satunnaiset kuvat, sitaatit, valuuttakurssit, kasvitietokannat, sanakirjat. Nämä haetaan oikeasti, mutta Kipinän oman proxyn kautta jotta API-avaimet pysyvät palvelimella ja kulutusta voidaan rajoittaa.

**Taso 2: Simuloitu käyttäjädata.** Jos konsepti vaatii käyttäjän omaa kalenteridataa, viestejä tai sijaintia, Mestari käyttää **realistisen näköistä simuloitua dataa** (esim. mock-kalenterin "keskiviikkoni"). Pilotissa ei tehdä oikeaa OAuth-virityksiä tai käyttäjätilien kytkemistä.

### API-proxy-palvelu

Uusi backend-palvelu (`kipina-api-proxy`, alustavasti portti 8085) joka:
- Tarjoaa kaikki templatessa kuvatut tietolähteet Kipinän oman domainin alta (`/api/templates/*`)
- Piilottaa varsinaiset API-avaimet palvelimelle
- Rajoittaa kutsumäärää per sandbox/sessio jotta yksi prototyyppi ei syö budjettia

Tämän palvelun yksityiskohdat ja templaten formaatti kuvataan **B-dokumentissa**. Pilotin ensimmäisessä versiossa otetaan mukaan **10–15 templatea** jotka kattavat yleisimmät tarpeet.

### Vaikutus Mestariin

Mestarin system instructionseihin liitetään tiivistetty kuvaus käytettävissä olevista templateista. Mestari:
- Lukee konseptin "Tarvittavat tietovirrat" -osion
- Valitsee siihen sopivat templatet
- Generoi prototyyppiin koodin joka kutsuu templateja Kipinän proxyn kautta
- Ei tee muita ulkoisia kutsuja

Jos konseptissa on tietovirta jolle ei ole templatea, Mestari simuloi sen tyydyttävällä mockilla — ei yritä keksiä oikeaa palvelua.

---

## 7. Kustannusarvio — riittääkö 855€?

Kustannusten karkea arvio koostuu kolmesta osasta:

### 7.1 Gemini 3 Pro -kutsut

Vibekoodausistunnossa Mestari tekee tyypillisesti useita LLM-kutsuja: alkuperäinen prototyyppi (1 iso kutsu), iteraatiot (5–20 per istunto), Pohdinta-vuorot. Karkea arvio per istunto: ~30 000 input-tokenia + ~15 000 output-tokenia = noin 2€ Gemini 3 Pro -hinnoittelulla.

### 7.2 Agent Engine Code Execution -sandboxit

Sandbox-tunnit hinnoitellaan käytön mukaan. Tunnin TTL:llä yksi istunto kuluttaa korkeintaan yhden sandbox-tunnin. Karkea arvio per istunto: alle 1€.

### 7.3 Speech-to-Text -minuutit

Tyypillisessä istunnossa nuori puhuu ehkä 2–5 minuuttia yhteensä. Google Cloud STT:n hinnoittelu suomelle pyörii 0,5–1 sentin tienoilla minuutilta. Per istunto: muutama sentti.

### 7.4 Template API -kutsut

Useimmat templatekirjaston tietolähteet ovat ilmaisia tai erittäin halpoja (ilmatieteenlaitoksen avoin data, OpenStreetMap, Lorem Picsum, Wikipedia-API). Maksulliset (esim. kaupalliset karttapalvelut, kuvantunnistus) pidetään tiukassa kulutusrajassa proxyssä. Per istunto: arviolta alle 10 senttiä.

### 7.5 Yhteensä per istunto

Karkea arvio: **2,5–5€ per täysi vibekoodausistunto** (sisältää Tools-käytön ~25% lisäkustannuksen, jos Mestari hyödyntää Google Search / URL Context -työkaluja noin puolessa iteraatioista).

855€ creditiltä saadaan siis **170–340 vibekoodausistuntoa**. Pilotille tämä on edelleen riittävä.

Tarkat luvut pitää varmistaa B-dokumentissa nykyisten hintojen perusteella ja todellinen kulutus seurantaan deploymentin jälkeen.

---

## 8. Riskit ja avoimet kysymykset

### 8.1 Tekniset riskit

**Code Execution us-central1 -aluerajoitus** — Concept API on `europe-west4`, Prototype API joudutaan laittamaan `us-central1`. Tämä ei ole tietosuojaongelma koska konsepti on jo DLP-puhdistettu, mutta se on operatiivinen yksityiskohta jonka pitää näkyä B-dokumentissa.

**Iframen turvallisuus** — Mestarin tuottama HTML pyörii iframessa Kipinän sivulla. Iframe pitää `sandbox`-attribuutilla rajoittaa siten että prototyyppi ei voi tehdä haittaa Kipinälle. Tämä on C-dokumentin yksityiskohta.

**Sandbox-TTL ja sessio-katkokset** — Jos nuori on tauolla yli tunnin, sessio katkeaa. Pitää päättää onko aloituspainike tarpeeksi selkeä ("Aloita uusi vibe") vai tarvitaanko parempaa palautumismekanismia. Pilotissa: kevyt versio riittää.

### 8.2 Designriskit

**Mestarin "muistutus" voi tuntua kontrolloivalta** — Liian tiheät muistutukset konseptista voivat tuntua holhoukselta. Pitää säätää system instructionseissa siten, että muistutus tulee enintään kerran istunnon aikana ja vain selvästi sivuraidalle ajauduttaessa.

**Pohdinta-tilan epäselvyys** — Nuori ei välttämättä erota milloin haluaa Koodaus- vai Pohdinta-tilaa. Pilotissa: pidetään oletuksena Koodaus, ja Mestari ohjeistaa Pohdinta-tilan käyttöön ensimmäisessä ohjeessaan (esim. "Jos haluat vain keskustella ilman muutoksia, vaihda Pohdinta-tilaan.").

### 8.3 Pilotin rajaukset

Tietoisesti **EI mukana** tässä vaiheessa:
- Prototyyppien pysyvä tallennus
- Useamman session yhdistäminen samasta konseptista
- Prototyypin export-toiminto (esim. ZIP-lataus)
- Mestarin oppiminen aiemmista istunnoista
- Useamman nuoren yhteistyö samassa istunnossa

Nämä voidaan käsitellä myöhemmissä versioissa kun pilotti on tuottanut oppimista.

---

## 8.5 Auditoidut poikkeukset

Pilotissa on tietoisia poikkeuksia yleisistä periaatteista (kuten "kaikki DLP:n läpi"). Nämä on dokumentoitu auki jotta:

- Tulevat LLM-avustajat tai uudet kehittäjät eivät "korjaa" niitä rikkoen alkuperäisen käyttötarkoituksen
- Tietosuojakatselmoinneissa poikkeuksen olemassaolo on selitettävissä
- Mahdolliset auditointitilanteet osoittavat että poikkeukset ovat hallittuja, eivät vahinkoja

### 8.5.1 Mestari-Suosittelijan DLP-poikkeus

`POST /api/prototype/suggest-iteration` -endpoint (kuvattu B-dokumentissa) **ei aja DLP:tä** ennen tai jälkeen Gemini-kutsun. Syy: endpoint on superadmin-only testaustyökalu joka generoi raakaa keksittyä käyttäjäsyötettä Mestarin DLP-mekanismin testaamiseen. Jos DLP suodattaisi tämän, Mestarin DLP-toimintaa ei voisi enää testata realistisilla syötteillä. Pääsy on rajattu superadmin-roolille (`X-Kipina-Superadmin-Key`-header).

Tämä poikkeus on saanut inspiraationsa Varpun samasta arkkitehtuuripäätöksestä (Varpun `/api/varpu/admin/agent/suggest`-endpoint), ja noudattaa samaa periaatetta: testaustyökalujen ei pidä esikäsitellä syötteitä joiden testaamiseen ne on rakennettu.

---

## 9. Päätökset jotka pitää lukita ennen B- ja C-dokumentteja

Ennen kuin etenen B-dokumenttiin (backend), seuraavat asiat pitää vahvistaa tai keskustella:

1. **Mestari-rooli ja äänensävy** — onko kuvaus kohdallaan vai tarvitaanko muutoksia?
2. **Koodaus/Pohdinta-jako** — toimiiko kahden tilan malli vai pitäisikö olla yksi tila jossa Mestari itse päättää milloin koodaa ja milloin keskustelee?
3. **Konseptiuskollisuusperiaate** — kuinka voimakas muistutusmekanismi Mestarilla saa olla?
4. **Sandboxin TTL** — riittääkö tunti, vai pitäisikö pilotissa olla pidempi (esim. 4h) jotta nuori voi pitää tauon kesken?
5. **Ensimmäinen prototyyppi** — generoiko Mestari sen automaattisesti session alussa, vai odottaako ensimmäistä nuoren pyyntöä?
6. **Template Libraryn kattavuus** — keskilaaja (10–15 templatea) on linjattu, mutta tarkka lista templateista tehdään B-dokumentissa. A-tasolla riittää että periaate on hyväksytty.

---

## 10. Liitteet ja viittaukset

- **Rautalanka**: `kipina-vibe-rautalanka.html` (latasit chatissa 2026-05-28)
- **Reveal Engine**: GitHub `reveal-api-kanavana`
- **Reveal Platform**: deploy `pilot.kipina.digiter.fi` -ympäristössä
- **Concept API**: `concept-api-implementation.md` (projektikansiossa)
- **Tenantit (Reveal Platform)**: mina, mina-ja-toinen, porukka, maailma, emma-tiia (kaikki v2-tasolla)
- **GCP-projekti**: `apply-project-35406`
- **GCP-krediitit pilotille**: 855€

---

*Loppu A-dokumentista. Seuraavaksi B (backend) ja C (frontend) — vasta kun A on hyväksytty.*
