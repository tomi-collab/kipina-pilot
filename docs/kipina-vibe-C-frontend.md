# Kipinä Vibe — C. Frontend

**Dokumentti:** C/3 (Frontend)
**Päivätty:** 2026-05-28
**Kirjoittaja:** Tomi Turpeinen + Claude (suunnittelukeskustelu)
**Tila:** Luonnos kommentoitavaksi
**Edellyttää:** A- ja B-dokumentit hyväksytty

---

## 1. Yleiskuva

C-dokumentti kuvaa Kipinän React-frontendin laajennuksen, jolla vibekoodausvaihe saadaan käyttöön. Yksi uusi näkymä (VibeStudioView), yksi uusi reitti, yksi uusi tilanhallintamoduuli, kolme uutta API-kutsujen kääreitä.

### 1.1 Suunnitteluperiaate: mobile-first

**Mobiililayout on default. Desktop-versio on poikkeus johon lisätään tilaa.**

Tämä koskee jokaista komponenttia, jokaista tyyliä ja jokaista vuorovaikutuskuviota. Kun komponentti suunnitellaan, lähdetään liikkeelle 380px-leveydestä. Tailwindin breakpointit (`md:`, `lg:`) lisäävät tilaa ja muuttavat layoutia desktop-kontekstissa, mutta perustoiminta toimii ilman niitä.

Nuoret eivät välttämättä käytä työasemia. Joissakin perheissä koko digikäyttö tapahtuu puhelimella. Mobiilin pitää olla ensiluokkainen kokemus, ei minimoitu desktop-näkymä.

### 1.2 Mitä rakennetaan

| Komponentti | Tyyppi | Vastuu |
|-------------|--------|--------|
| `VibeStudioView` | Sivu (route `/vibe/:sessionId`) | Vibekoodausnäkymä |
| `VibePreview` | Komponentti | Iframe live preview prototyypille |
| `VibeControls` | Komponentti | Kontrollipaneeli (prompt, mikki, pikatoiminnot, mode-toggle, päivitys) |
| `VibeMicButton` | Komponentti | Push-to-talk -mikkinappula |
| `VibeQuickActions` | Komponentti | Pikatoimintonapit |
| `VibeModeToggle` | Komponentti | Koodaus/Pohdinta -kytkin |
| `VibeMestariNote` | Komponentti | Mestarin huomio -kenttä |
| `VibeDrawer` | Komponentti | Mobiilin liukupaneeli |
| `VibeConceptModal` | Komponentti | "Näytä konsepti" -modal alkuperäisestä konseptista |
| `VibeHistoryModal` | Komponentti | "Mitä mä äsken sanoin" -modal session-iteraatioista |
| `VibeSuggestionPanel` | Komponentti | Mestari-Suosittelija (vain superadmin-roolissa näkyvä) |
| `useVibeSession` | Hook | Session-tila, API-kutsut, undo-stack |
| `useSpeechRecorder` | Hook | MediaRecorder-äänen tallennus |
| `vibeApi.ts` | Moduuli | Prototype API + STT Proxy -kutsujen kääreet |

---

## 2. Käyttäjäpolku rautalangan mukaan

Lähtötilanne: nuori on konseptinäkymässä, on lukenut konseptin.

### 2.1 Vibekoodausvaiheen aloitus

1. Konseptinäkymässä nappi **"Aloita vibekoodaus"** (nykyisen "Tee prototyyppi" -placeholderin paikalla)
2. Painallus → kutsu `POST /api/prototype/start`
3. Frontend näyttää loading-tilan ("Mestari valmistelee ensimmäistä versiota...")
4. Onnistuessa siirtyy reittiin `/vibe/:sessionId` ja VibeStudioView avautuu
5. Ensimmäinen prototyyppi näkyy iframessa, Mestarin huomio -kentässä lyhyt viesti

### 2.2 Iteraatio

Nuori voi (mobiilissa):
1. **Avata kontrollipaneelin** swipettämällä alas-ylös, klikkaamalla tai painamalla huomio-kenttää
2. **Puhua** pitämällä mikkinappulaa pohjassa → STT muuntaa puheen tekstiksi promptikenttään
3. **Kirjoittaa** suoraan promptikenttään (näppäimistö ilmestyy)
4. **Painaa pikatoimintoa** → täyttää promptikentän valmiilla tekstillä
5. **Vaihtaa tilaa** (Koodaus ↔ Pohdinta) toggle-kytkimellä
6. **Painaa Päivitys-nappia** → lähettää pyynnön Mestarille

Vastaus palautuu, iframe päivittyy (Koodaus) tai Mestarin huomio päivittyy (Pohdinta).

### 2.3 Undo

Pitkä painallus prompt-tekstikentän vieressä olevaa **undo-nappia** palauttaa edellisen version. Nappi on disabled jos historiaa ei ole.

### 2.4 Session päätös

Pilotissa ei automaattista lopetusta. Nuori palaa takaisin nuoli-napin kautta. Sandbox jää elämään TTL:n loppuun, mutta selaintilasta poistetaan referenssi.

---

## 3. VibeStudioView — pääkomponentti

### 3.1 Reititys

`/vibe/:sessionId` — uusi reitti React Routeriin. Reitti suojataan samalla pääsykoodi-suojauksella kuin muutkin Kipinän näkymät.

### 3.2 Mobile-layout (default, < 768px)

```
┌─────────────────────────────────┐
│ ← Takaisin   📄 Konsepti        │ ← topbar 56px
├─────────────────────────────────┤
│                                 │
│                                 │
│                                 │
│       <iframe srcdoc=...>       │ ← VibePreview täyttää loput
│                                 │
│                                 │
│                                 │
│                                 │
├─────────────────────────────────┤
│  ───  (swipe-kahva)             │ ← VibeDrawer, kiinni 100px
│  Mestari: lyhyt teksti          │ ← Mestarin huomio aina näkyvissä,
│  joka voi olla kahdella rivillä │   mahtuu kahdelle riville
└─────────────────────────────────┘
```

Drawer auki:

```
┌─────────────────────────────────┐
│ ← Takaisin        Mestari ●     │
├─────────────────────────────────┤
│       <iframe srcdoc=...>       │ ← Preview pieneksi puristettu
├─────────────────────────────────┤
│ ───                             │
│ NUOREN VIBE / OHJE              │
│ ┌─────────────────────────────┐ │
│ │ Mitä muutetaan?             │ │ ← textarea
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ [✨ Vaihda tyyliä] [📱 Mobiili]│ ← pikatoiminnot
│                                 │
│ ┌─ Koodaus  [●○]  Pohdinta ─┐  │ ← mode-toggle
│ │                            │  │
│ │         ╭─────╮            │  │
│ │         │ 🎤  │            │  │ ← mikkinappula iso, 80px
│ │         ╰─────╯            │  │
│ │      Pidä pohjassa         │  │
│ │      ja puhu               │  │
│ └────────────────────────────┘  │
│                                 │
│ [PÄIVITYS]      [↶ Undo]        │ ← actions
└─────────────────────────────────┘
```

### 3.3 Desktop-layout (≥ 768px)

Kaksi pystysaraketta:
- **Vasemmalla**: kontrollipaneeli (sidebar, 320–384px leveä, ei drawer)
- **Oikealla**: iframe preview täyttää loput

Iframe ei pienene avatessa, koska sidebar on aina näkyvissä.

### 3.4 Tilankäsittely

```typescript
interface VibeSessionState {
  sandboxId: string | null;
  sessionId: string;
  prototypeHtml: string;
  mestariMessage: string;
  mode: 'koodaus' | 'pohdinta';
  iterationCount: number;
  drawerOpen: boolean;          // vain mobiili
  isLoading: boolean;
  isRecording: boolean;
  promptText: string;
  conceptDriftWarning: string | null;
  undoStack: string[];          // edellisten HTML-versioiden referenssit (paikallinen)
  canUndo: boolean;
}
```

Tila hallinnoidaan `useVibeSession`-hookilla (ks. luku 8.1).

---

## 4. VibePreview — iframe live preview

### 4.1 Iframe-sandbox

```tsx
<iframe
  className="w-full h-full border-none"
  srcDoc={prototypeHtml}
  sandbox="allow-scripts"
  title="Prototyyppi"
/>
```

Sandbox-attribuutti rajaa iframen oikeudet (vrt. B-dokumentti 7.1):
- `allow-scripts` → JavaScript pyörii
- Ei `allow-same-origin` → ei pääsyä Kipinän cookieihin
- Ei `allow-forms` → ei form-submitia
- Ei `allow-popups` → ei pop-uppeja
- Ei `allow-top-navigation` → ei sivun uudelleenohjausta

### 4.2 srcdoc vs. blob URL

`srcDoc` on yksinkertaisempi: HTML-string menee suoraan attribuuttiin, ei tarvita URL.createObjectURL-hallintaa. Pilottivolyymeillä HTML on alle 50 KB, joten srcdoc on riittävä.

### 4.3 Päivitysstrategia

Kun `prototypeHtml` muuttuu (uusi iteraatio), iframe rerendaa automaattisesti React-tasolla. Tämä on ok pilotissa: nuoren ei pitäisi olla iframen sisällä keskellä toimintaa kun muutos tulee — hän tekee pyynnön Päivitys-napilla ja odottaa.

Tulevaisuudessa voi harkita morph-tyyppistä päivitystä (esim. `htmx`-tyyliset partial updatet), mutta pilotissa kokonainen rerender on yksinkertaisin ja toimiva.

### 4.4 Lataustila

Kun `isLoading=true`, iframen päälle näytetään puolikvint peittokerros pulssaavalla viestillä ("Mestari koodaa..."). Vanha versio jää alle näkyväksi jotta nuori näkee mistä lähdettiin.

---

## 5. VibeControls — kontrollipaneeli

### 5.1 Promptikenttä

```tsx
<textarea
  className="w-full bg-slate-800 border border-slate-700 rounded-2xl p-4
             text-sm focus:ring-2 focus:ring-emerald-500 outline-none
             h-24 md:h-32 resize-none"
  placeholder="Mitä muutetaan? Esim. 'Tee tästä neonvihreä'"
  value={promptText}
  onChange={e => setPromptText(e.target.value)}
  disabled={isLoading || isRecording}
/>
```

Kun mikkinappula on aktiivinen, kenttä näyttää reaaliaikaisen STT-tuloksen jos käytössä on streaming (tulevaisuudessa). Pilotissa: kenttä tyhjenee mikin painalluksen alussa, ja STT-tulos asetetaan kenttään kun puhe on lopetettu.

### 5.2 Pikatoiminnot

Rautalangassa kaksi nappia, mutta tämä on suunniteltu **laajennettavaksi listaksi**. Pikatoiminnot määritellään koodissa staattisena listana, ja niitä on helppo lisätä tai säätää.

```typescript
interface QuickAction {
  id: string;
  icon: string;            // emoji
  label: string;           // i18n-avain
  promptTemplate: string;  // teksti joka asetetaan promptikenttään
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'change-style',
    icon: '✨',
    label: 'vibe.quickActions.changeStyle',
    promptTemplate: 'Vaihda visuaalinen tyyli johonkin raikkaaseen.'
  },
  {
    id: 'mobile-optimize',
    icon: '📱',
    label: 'vibe.quickActions.mobileOptimize',
    promptTemplate: 'Optimoi tämä toimimaan paremmin puhelimella.'
  },
  {
    id: 'add-data',
    icon: '🔌',
    label: 'vibe.quickActions.addLiveData',
    promptTemplate: 'Tuo sovellukseen oikeaa dataa esim. säätieto tai joukkoliikennetieto.'
  },
  {
    id: 'simplify',
    icon: '✂️',
    label: 'vibe.quickActions.simplify',
    promptTemplate: 'Yksinkertaista sovellusta, jätä vain tärkein.'
  }
];
```

Mobiilissa näytetään 2x2 ruudukossa, desktopissa 1x4 tai 2x2 tilan mukaan. Painallus asettaa `promptText`-tilan ja **avaa näppäimistön** jotta nuori voi vielä muokata.

### 5.3 Mode-toggle (Koodaus / Pohdinta)

Rautalangan toggle-kytkin:
- Vasemmalla "Koodaus" (vihreä, oletus)
- Oikealla "Pohdinta" (sininen)
- Pyöreä indikaattori siirtyy

Tila ohjaa:
- Mikkinappulan väriä (vihreä/sininen)
- Päivitys-napin värin
- Lähetettävää `mode`-arvoa API-kutsussa

```tsx
<button
  className="w-12 h-6 bg-slate-700 rounded-full relative"
  onClick={() => setMode(mode === 'koodaus' ? 'pohdinta' : 'koodaus')}
  aria-label={mode === 'koodaus'
    ? t('vibe.mode.switchToPohdinta')
    : t('vibe.mode.switchToKoodaus')}
>
  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform
    ${mode === 'koodaus' ? 'left-1' : 'left-7'}`} />
</button>
```

### 5.4 Päivitys-nappi

Iso, näkyvä, kontrollipaneelin pohjalla:

```tsx
<button
  className={`w-full text-slate-950 font-bold py-4 rounded-2xl
              shadow-[0_0_20px_rgba(16,185,129,0.3)]
              transition-all transform active:scale-95
              ${mode === 'koodaus'
                ? 'bg-emerald-500 hover:bg-emerald-400'
                : 'bg-blue-500 hover:bg-blue-400'}`}
  onClick={handleSubmit}
  disabled={isLoading || !promptText.trim()}
>
  {isLoading ? t('vibe.updating') : t('vibe.update')}
</button>
```

Vieressä **Undo-nappi**, pienempi:

```tsx
<button
  className="px-4 py-4 bg-slate-800 hover:bg-slate-700 rounded-2xl
             disabled:opacity-40 disabled:cursor-not-allowed"
  onClick={handleUndo}
  disabled={!canUndo || isLoading}
  aria-label={t('vibe.undo')}
>
  ↶
</button>
```

---

## 6. VibeMicButton — push-to-talk -mikki

### 6.1 Vuorovaikutuslogiikka

Push-to-talk tarkoittaa: **paina ja pidä → nauhoittaa**, **vapauta → lopettaa ja lähettää STT:lle**. Tämä toimii erityisesti mobiilissa, jossa "klikkaa puhuaksesi / klikkaa lopettaaksesi" on hankalampi.

### 6.2 Kosketus + hiiri yhteinen logiikka

Käytetään Pointer Events -API:a, joka kattaa molemmat:

```tsx
<button
  ref={micRef}
  className={`w-20 h-20 rounded-full transition-all
              active:scale-90 select-none touch-none
              ${mode === 'koodaus'
                ? 'bg-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.4)]'
                : 'bg-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.4)]'}
              ${isRecording ? 'animate-pulse ring-4 ring-white/50' : ''}`}
  onPointerDown={startRecording}
  onPointerUp={stopRecording}
  onPointerLeave={stopRecording}
  onPointerCancel={stopRecording}
  aria-label={t('vibe.mic.holdToTalk')}
>
  <svg /* mikki-ikoni */ />
</button>
```

- `touch-none` estää selainta tulkitsemasta painallusta scrollaukseksi
- `onPointerLeave` ja `onPointerCancel` lopettavat nauhoituksen jos sormi liukuu pois napilta tai selain peruu eleen

### 6.3 useSpeechRecorder-hook

```typescript
interface SpeechRecorderHook {
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  isRecording: boolean;
  error: string | null;
}

function useSpeechRecorder(onTranscript: (text: string) => void): SpeechRecorderHook;
```

Toiminta:
1. `startRecording`: pyytää mikrofonioikeuden (getUserMedia), aloittaa MediaRecorder-nauhoituksen webm/opus-formaattiin
2. `stopRecording`: pysäyttää nauhoituksen, kokoaa Blob:n, lähettää STT Proxylle, kutsuu `onTranscript(text)` tuloksen kanssa
3. Maksimi nauhoituspituus 60 sekuntia (auto-stop) — STT Proxyn rajoitus

### 6.4 MediaRecorder-konfiguraatio

```typescript
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm;codecs=opus',
  audioBitsPerSecond: 16000  // riittävä puhelle, säästää bandwidtiä
});
```

Selaintukea varten: tarkistetaan että `MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` ennen kuin yritetään. Jos ei tuettu (Safari iOS:ssa joskus haastava), fallback `audio/mp4` tai virheviesti.

### 6.5 Mikrofonioikeuden käsittely

Ensimmäisellä painalluksella selain pyytää oikeuden. Jos käyttäjä hylkää:

```tsx
{error === 'permission_denied' && (
  <p className="text-xs text-amber-400 mt-2">
    {t('vibe.mic.permissionDenied')}
  </p>
)}
```

Käännös: "Mikrofoni ei ole sallittu. Voit kirjoittaa pyyntösi tekstinä."

---

## 7. VibeMestariNote — Mestarin huomio -kenttä

### 7.1 Sisältö

Kenttä näyttää Mestarin viimeisimmän viestin:
- Koodaus-tilassa: lyhyt kommentti tehdystä muutoksesta ("Vaihdoin värin vihreäksi.")
- Pohdinta-tilassa: pidempi keskusteluvastaus
- Concept drift -tilanteessa: muistutus alkuperäisestä konseptista

### 7.2 Visuaalinen erottelu drift-tilanteessa

```tsx
<div className={`p-4 rounded-2xl text-xs italic
  ${conceptDriftWarning
    ? 'bg-amber-500/10 border border-amber-500/30 text-amber-300'
    : 'bg-emerald-500/5 border border-emerald-500/10 text-emerald-400'}`}>
  {conceptDriftWarning || mestariMessage}
</div>
```

Drift-tilanteessa amber-väri viestii että Mestari kommentoi suuntaa, ei tehnyt vain teknistä muutosta.

### 7.3 Sijainti mobiilissa

Mestarin huomio näkyy **drawer-kahvan vieressä** vaikka drawer on kiinni. Tämä tarkoittaa että nuoren ei tarvitse avata paneelia nähdäkseen mitä Mestari sanoi. Drawer ei avaudu automaattisesti — nuori avaa sen kun haluaa reagoida.

### 7.4 VibeHistoryModal — "Mitä mä äsken sanoin"

Erillinen modal-komponentti joka näyttää session-aikaiset iteraatiot listana. Nuoret pystyvät palaamaan omiin sanoihinsa ilman että keskustelua tallennetaan pysyvästi mihinkään.

**Avaaminen:** Topbarissa pieni "🕓 Historia" -painike Konsepti-painikkeen vieressä. Painallus avaa modal-näkymän.

**Sisältö:** Lista iteraatioista uusin ensin, jokainen kortti sisältää:
- Iteraationumero (esim. "12.")
- Tila-merkki (Koodaus vihreä / Pohdinta sininen)
- Käyttäjän pyyntö ("Tee tästä neonvihreä")
- Mestarin vastaus ("Vaihdoin värin neonvihreäksi.")
- Aikaleima session alusta ("3 min sitten")

**Toiminta:**
- Lista latautuu kun modal avataan (kutsu `getHistory(sandboxId)`)
- Max 20 viimeisintä näytetään, jos enemmän iteraatioita on tehty, näytetään pieni teksti alalaidassa: "Näytetään 20 viimeisintä, kokonaisuudessaan {n}"
- Modal on luettava — ei voi suoraan klikata iteraatiota palautuakseen siihen (undo-toiminto hoitaa peruutuksen)

**Mobile-layout:**
- Modal täyttää koko ruudun
- Sulje-painike ylävasemmalla (← Takaisin)
- Lista skrollaa pystysuunnassa

**Toteutus on yksinkertainen:** ei monimutkaista tilankäsittelyä, modal-tilan ja iteraatioiden lataus useVibeSession-hookin sisällä, lokitietoja ei näytetä koska niitä ei ole.

### 7.5 Tärkeä periaatehuomio

Iteraatiohistoria näkyy nuorelle **vain session aikana**. Kun sandbox umpeutuu (1h TTL) tai nuori kirjautuu ulos, historia katoaa kokonaan. Tämä on linjassa Reveal-keskustelun periaatteen kanssa: työkalupuhe Mestarille ei elä pidempään kuin tehtävän tekeminen vaatii.

Frontendissä ei pidä antaa ymmärtää että historia säilyy. Sanamuoto "Mitä mä äsken sanoin" on tarkoituksellinen — viittaa nykyhetkeen, ei pidempään muistiin.

### 7.6 VibeSuggestionPanel — Mestari-Suosittelija (vain superadmin)

Erillinen testauspaneeli VibeStudioView'ssa, joka näkyy **vain superadmin-roolissa kirjautuneelle käyttäjälle**. Sen tehtävä on nopeuttaa Mestarin testausta: sen sijaan että testaaja keksii itse jokaisen uuden iteraatiopyynnön, generaattori ehdottaa seuraavan vuoron pyynnön Gemini-mallin avulla, testaaja näkee ehdotuksen, voi muokata sitä ja sitten lähettää Mestarille.

Tämä on **testaustyökalu, ei tuotantokomponentti**. Tavalliset nuoret eivät näe paneelia.

**Käyttöperiaate (Varpun mallin mukainen):**

1. Superadmin-rooli aktivoituu pääsykoodilla tai erillisellä tunnuksella (pilotissa: ympäristömuuttuja `KIPINA_SUPERADMIN_KEY` jonka testaaja syöttää selaimen sessionStorageen kerran)
2. Kun superadmin on VibeStudioView'ssa, kontrollipaneelissa näkyy "💡 Ehdota iteraatio" -painike Päivitys-napin lähellä
3. Painallus avaa pienen modal- tai expanderin, jossa Gemini generoi 1–3 ehdotusta seuraavalle iteraatiopyynnölle
4. Ehdotukset perustuvat: nykyiseen prototyyppi-HTML:ään, viimeisimpiin iteraatioihin, ja Mestarin alkuperäiseen konseptiin
5. Testaaja valitsee ehdotuksen, joka asettuu promptikenttään → voi muokata vapaasti → painaa Päivitys → menee normaalia putkea Mestarille

**Auditoitava poikkeus:**

`/api/prototype/suggest-iteration`-endpoint **ei aja DLP:tä** ennen Gemini-kutsua. Tämä on tarkoituksellinen valinta:

- Suosittelija generoi raakaa keksittyä käyttäjäsyötettä (esim. testaajaa varten "lisää Aminan nimi etusivulle" — jossa Amina on keksitty)
- DLP:n oikea testipaikka on Mestarin Prototype API, jonne ehdotus joka tapauksessa päätyy
- Jos DLP söisi keksityt nimet ennen Geminiä, koko DLP-mekanismia ei voisi testata realistisilla syötteillä
- Pääsy on rajoitettu superadminille — ei loppukäyttäjäpolku

Tämä poikkeus pitää **dokumentoida koodissa kommenttina sekä Kipinän tietosuojadokumentaatiossa**, jotta tulevat LLM-avustajat tai uudet kehittäjät eivät "korjaa" sitä lisäämällä DLP:n väliin ja rikkoo testaustyökalua.

**Toteutus:**

- Frontend: VibeSuggestionPanel-komponentti renderöidään ehdollisesti `user.role === 'superadmin'`-tarkistuksen pohjalta
- Backend: uusi endpoint `POST /api/prototype/suggest-iteration` Prototype API:ssa (B1-palvelu), kuvattu briefissa
- Gemini-malli: sama `gemini-2.5-pro` kuin Mestarilla, mutta erillinen system instruction ("Olet testausagentti joka generoi uskottavia käyttäjäpyyntöjä Kipinän nuorten prototyyppisuunnittelijoiden tyyliin...")

**Mitä myöhempiin vaiheisiin (ei C1:ssä):**

- **Autonominen sessio-ajuri** (Varpun osa 2 -malli) — erillinen palvelu portissa 8093, ei Caddyn takana, ajaa kokonaisia vibe-sessioita läpi automaattisesti regressiotestausta varten. Toteutetaan kun Mestari on vakiintunut.

---

## 8. Tilanhallinta ja API-kutsut

### 8.1 useVibeSession-hook

```typescript
interface VibeSessionHook {
  state: VibeSessionState;
  startSession: (concept: string, report: string, tenantId: string) => Promise<void>;
  iterate: (input: string) => Promise<void>;
  undo: () => Promise<void>;
  switchMode: (mode: 'koodaus' | 'pohdinta') => void;
  setPromptText: (text: string) => void;
  toggleDrawer: () => void;
}

function useVibeSession(sessionId: string): VibeSessionHook;
```

Toteutuksen periaatteet:
- Session-tila pidetään hookin sisällä `useReducer`-tilakoneena
- Tila tallennetaan myös `sessionStorage`en (selain-sessio) jotta sivun uudelleenlataus ei nollaa tilaa
- API-kutsujen virheet tallennetaan tilaan ja näytetään käyttäjälle
- Undo-stack pidetään tilassa, mutta varsinainen historia on Prototype API:n muistissa — frontend vain tietää kuinka monta askelta taaksepäin on saatavilla (`canUndo`-flagi)

### 8.2 vibeApi.ts — API-kutsujen kääre

```typescript
// vibeApi.ts

export async function startPrototype(payload: {
  concept: string;
  report: string;
  tenantId: string;
  sessionId: string;
}): Promise<StartResponse> {
  const r = await fetch('/api/prototype/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!r.ok) throw new Error(`Start failed: ${r.status}`);
  return r.json();
}

export async function iteratePrototype(payload: {
  sandboxId: string;
  mode: 'koodaus' | 'pohdinta';
  userInput: string;
  language: string;
}): Promise<IterateResponse> {
  const r = await fetch('/api/prototype/iterate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!r.ok) throw new Error(`Iterate failed: ${r.status}`);
  return r.json();
}

export async function undoPrototype(sandboxId: string): Promise<UndoResponse> {
  const r = await fetch('/api/prototype/undo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sandbox_id: sandboxId })
  });
  if (!r.ok) {
    if (r.status === 400) throw new Error('no_undo_available');
    throw new Error(`Undo failed: ${r.status}`);
  }
  return r.json();
}

export async function transcribeSpeech(audioBlob: Blob, language = 'fi-FI'): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  form.append('language', language);
  const r = await fetch('/api/stt/transcribe', { method: 'POST', body: form });
  if (!r.ok) throw new Error(`Transcribe failed: ${r.status}`);
  return r.json();
}
```

### 8.3 Concept drift -muistutuksen ajoitus

Frontend kutsuu `/api/prototype/remind-check`-endpointtia kerran istunnon aikana, **10. iteraation kohdalla**. Jos vastaus `should_remind=true`, näytetään Mestarin huomio drift-tyylillä.

Vaihtoehtoisesti: Mestari voi itse asettaa `concept_drift_warning`-kentän `/iterate`-vastauksessa. Tämä on yksinkertaisempi ja vaatii vähemmän erillisiä kutsuja. Päätös B-dokumentin luvussa 10.2.2.

### 8.4 Virheenkäsittely

| Tilanne | UI |
|---------|-----|
| Verkkovirhe | Toast: "Yhteys katkesi. Yritä uudelleen." |
| Sandbox expired (TTL) | Modal: "Sessio päättyi. Aloita uusi vibekoodaus." → palauttaa konseptinäkymään |
| STT-virhe (mikkiongelma) | Inline-viesti mikkinappulan alla: "Mikrofoniongelma, kirjoita pyyntö." |
| Undo not available | Disabled-nappi, tooltip "Ei peruutettavaa." |
| Prototype API 502 (Mestari ei vastannut) | Toast: "Mestari ei juuri nyt vastaa. Yritä uudelleen." |

---

## 9. Drawer-logiikka mobiilissa

### 9.1 Tilat

- **Kiinni**: vain 100px näkyvissä alalaidasta — swipe-kahva + Mestarin huomio -kenttä, johon mahtuu kahden rivin viesti ilman leikkautumista
- **Auki**: koko paneeli näkyvissä, peittää iframen alapuolen

### 9.2 Tilan vaihto

Drawer voidaan avata/sulkea kolmella tavalla:

1. **Pyyhkäisy** swipe-kahvan kautta (touchstart + touchend, diff > 30px)
2. **Klikkaus** swipe-kahvalle (pienen liikkeen tunnistuksella)
3. **Painallus Mestarin huomio -kenttään**

Lähde: rautalangan JS-toteutus on hyvä pohja. Lisätään React-Hookkien yhteyteen.

### 9.3 Animaatio

```css
.drawer {
  transform: translateY(calc(100% - 100px));
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer.open {
  transform: translateY(0);
}
```

`cubic-bezier(0.4, 0, 0.2, 1)` on Material Designin standard-easing — nopea alku, hidas loppu, tuntuu luonnolliselta.

### 9.4 Näppäimistön avautuminen

Mobiilissa kun nuori klikkaa promptikenttää, virtuaalinäppäimistö avautuu ja vie tilaa. Tämä on iOS/Android-käyttäytymistä joka pitää huomioida:

- iOS: `visualViewport` API kertoo todellisen näkyvän alueen → drawer skaalautuu automaattisesti
- Android: vaihtelevampi, mutta yleensä viewport kutistuu

Käytännössä: textareaa ei pidä laittaa drawerin pohjalle vaan yläosaan, jotta näppäimistö ei peitä sitä. Rautalangassa textarea on jo korkealla, hyvä.

### 9.5 Pyyhkäisyrajat

Drawerin pyyhkäisy ei saa lähteä iframen sisältä — muuten käyttäjä yrittää scrollata prototyyppiä ja drawer avautuu vahingossa. Pyyhkäisy tunnistetaan vain swipe-kahvalta + Mestarin huomio -kentästä, ei iframen päältä.

---

## 10. i18n-laajennukset

### 10.1 Uudet käännösavaimet

Lisätään `fi.ts` ja `en.ts` -tiedostoihin uusi `vibe`-objekti:

```typescript
// fi.ts
vibe: {
  startButton: 'Aloita vibekoodaus',
  startLoading: 'Mestari valmistelee ensimmäistä versiota…',
  preparing: 'Mestari koodaa…',
  update: 'PÄIVITYS',
  updating: 'Päivitetään…',
  undo: 'Peruuta',
  back: 'Takaisin konseptiin',
  promptPlaceholder: "Mitä muutetaan? Esim. 'Tee tästä neonvihreä'",

  mode: {
    koodaus: 'Koodaus',
    pohdinta: 'Pohdinta',
    switchToPohdinta: 'Vaihda pohdintaan',
    switchToKoodaus: 'Vaihda koodaukseen'
  },

  mic: {
    holdToTalk: 'Pidä pohjassa ja puhu',
    recording: 'Nauhoittaa…',
    permissionDenied: 'Mikrofoni ei ole sallittu. Voit kirjoittaa pyyntösi.',
    notSupported: 'Mikrofoni ei ole saatavilla tällä laitteella.'
  },

  quickActions: {
    changeStyle: 'Vaihda tyyliä',
    mobileOptimize: 'Mobiilioptimoitu',
    addLiveData: 'Lisää oikeaa dataa',
    simplify: 'Yksinkertaista'
  },

  errors: {
    sessionExpired: 'Sessio päättyi. Aloita uusi vibekoodaus.',
    sessionExpiredAction: 'Aloita uudelleen',
    networkError: 'Yhteys katkesi. Yritä uudelleen.',
    mestariNotResponding: 'Mestari ei juuri nyt vastaa. Yritä uudelleen.',
    noUndoAvailable: 'Ei peruutettavaa.'
  },

  driftWarning: {
    title: 'Mestari huomauttaa',
    keepConcept: 'Pidetäänkö kiinni alkuperäisestä?'
  },

  concept: {
    show: 'Näytä konsepti',
    title: 'Sinun ideasi',
    showOriginalConversation: 'Näytä myös alkuperäinen keskustelu',
    close: 'Sulje'
  }
}
```

Englanninkielinen vastine `en.ts`:ssa identtisellä rakenteella.

### 10.2 Mestarin viestit

Mestarin viestit tulevat Prototype API:lta valmiina suomeksi (tai englanniksi `language`-parametrin mukaan). Niitä ei käännetä frontendissä — ne ovat dynaamista sisältöä, ei UI-tekstejä.

---

## 11. Tyylit ja Tailwind

### 11.1 Tailwind-konfiguraatio

Pilotissa Tailwind CDN on käytössä (rautalanka näytti tämän). Tuotannossa siirrytään build-pohjaiseen Tailwindiin Viten kautta:

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

`tailwind.config.js`:n `content`-polut osoittavat React-komponentteihin:

```javascript
content: [
  './index.html',
  './src/**/*.{js,jsx,ts,tsx}'
]
```

### 11.2 Värisuunnitelma

Rautalangan mukaisesti:
- **Tausta**: `bg-slate-950` (tumma)
- **Paneelit**: `bg-slate-900`, `border-slate-700`
- **Koodaus-tila**: `emerald-500` (vihreä)
- **Pohdinta-tila**: `blue-500` (sininen)
- **Drift-varoitus**: `amber-400` (oranssi)
- **Teksti**: `slate-100` (vaalea), `slate-400` (himmennetty)

### 11.3 Pyöristykset ja varjot

Iso pyöristys (`rounded-2xl`, `rounded-3xl`) tuo pehmeyttä joka sopii nuorten käyttöliittymään. Glow-tyyliset varjot (`shadow-[0_0_30px_rgba(16,185,129,0.4)]`) painottavat mikkinappulaa ja Päivitys-nappia.

### 11.4 Eleet ja palaute

- `active:scale-90` mikkinappulalle ja Päivitys-napille — kosketuspalaute
- `animate-pulse` nauhoittaessa
- `animate-ping` mikkinappulan reunalle painalluksen aikana

Nämä toimivat hyvin sekä kosketuksella että hiirellä.

---

## 12. Esteettömyys (a11y)

Nuoria käyttäjiä on monenlaisia. Perustaso esteettömyydestä on välttämätön.

### 12.1 ARIA-labelit

Kaikilla interaktiivisilla elementeillä:

```tsx
<button aria-label={t('vibe.mic.holdToTalk')}>...</button>
<button aria-label={t('vibe.undo')}>...</button>
<input aria-label={t('vibe.promptPlaceholder')} />
```

### 12.2 Kontrasti

Tumma tausta + vaalea teksti antaa hyvän kontrastin. Varmistetaan että amber-, emerald- ja blue-tekstit täyttävät WCAG AA -tason normaalia tekstiä vasten.

### 12.3 Näppäimistönavigaatio

Tabista pitää voida liikkua: promptikenttä → pikatoiminnot → mode-toggle → mikki → Päivitys → undo. Enter Päivitys-napilla lähettää. Esc sulkee drawerin mobiilissa.

### 12.4 Reduced motion

`prefers-reduced-motion: reduce` poistaa pulse-animaation ja kovettaa drawerin animaation:

```css
@media (prefers-reduced-motion: reduce) {
  .drawer { transition: none; }
  .animate-pulse, .animate-ping { animation: none; }
}
```

---

## 13. Suorituskyky

### 13.1 Iframen uudelleenrender

Kun `prototypeHtml` muuttuu, React renderöi iframen uudelleen ja selain parsii koko HTML:n. Tämä on aika kallista operaatio, mutta tapahtuu vain käyttäjän eksplisiittisen pyynnön jälkeen — ei jatkuvasti.

### 13.2 STT-lähetys

Webm-äänitiedosto 60 sekunnilta on noin 100–200 KB. Tämä menee STT Proxylle yhtenä HTTP POST -kutsuna. Ei merkittävää suorituskykyongelmaa.

### 13.3 Bundle-koko

VibeStudioView lisää bundle-kokoa: uusi näkymä + hookit + API-moduuli. Arvio: noin 15–25 KB minifioituna (ei iso). Tailwind- ja React-runtime ovat jo bundlessa.

---

## 14. Testaus

### 14.1 Käsintestaus

Pilotissa testataan ensisijaisesti käsin oikealla puhelimella:
- Android (Chrome) — laaja yleisö nuorten keskuudessa
- iOS (Safari) — toinen iso ryhmä
- Pieni Android-puhelin (esim. iPhone SE -kokoluokka) — tila on tiukimmillaan

Testattavat polut:
1. Aloita vibekoodaus, ensimmäinen versio latautuu
2. Avaa drawer pyyhkäisemällä, kirjoita pyyntö, paina Päivitys
3. Avaa drawer, paina mikkiä, puhu "tee siitä sininen", vapauta, paina Päivitys
4. Vaihda Pohdinta-tilaan, kysy kysymys, varmista että iframe ei muutu
5. Tee 3 muutosta peräkkäin, paina undo kahdesti, varmista että versiot palautuvat
6. Mene tekstikentällä, näppäimistö avautuu, ei peitä tekstiä

### 14.2 Automaattitestit

Pilotissa ei rakenneta laajaa automaattitestiä, mutta yksittäisille kriittisille komponenteille (`useVibeSession`-tilakone, `vibeApi`-kutsut) yksikkötestit Vitestillä jos aikaa on.

---

## 15. Vaiheistus

Kuten B:ssä, jaetaan toteutus kolmeen vaiheeseen.

### Vaihe C1: VibeStudioView + Prototype API -integraatio

**Tavoite:** Toimiva vibekoodausnäkymä, ensimmäinen versio + iteraatiot Koodaus-tilassa, tekstillä (ei mikkiä vielä).

**Tehtävät:**
1. Lisää `/vibe/:sessionId`-reitti React Routeriin
2. Toteuta VibeStudioView, VibePreview, VibeControls (perusmuoto)
3. Toteuta `useVibeSession`-hook ja `vibeApi.ts`
4. Toteuta drawer mobiilissa, sidebar desktopissa
5. Lisää konseptinäkymään "Aloita vibekoodaus" -nappi
6. Lisää käännösavaimet `vibe.*`

**Riippuvuudet:** B1 valmis (Prototype API toimii).

### Vaihe C2: Mode-toggle + Pohdinta-tila + Undo + pikatoiminnot

**Tavoite:** Täysi UI-feature-set ilman mikkiä.

**Tehtävät:**
1. Lisää VibeModeToggle, switch-logiikka
2. Lisää VibeMestariNote drift-tyylillä
3. Lisää undo-nappi ja `undoPrototype`-kutsu
4. Lisää pikatoiminnot ja niiden prompt-pohjat
5. Lisää virheviestit ja toast-komponentti

**Riippuvuudet:** C1 valmis.

### Vaihe C3: Mikkinappula + STT-integraatio

**Tavoite:** Push-to-talk -mikki toimii oikealla puhelimella.

**Tehtävät:**
1. Toteuta `useSpeechRecorder`-hook (MediaRecorder)
2. Toteuta VibeMicButton push-to-talk -logiikalla
3. Integroi STT Proxy -kutsu (`transcribeSpeech`)
4. Testaa Android Chromessa ja iOS Safarissa
5. Lisää virheviestit mikrofoniongelmiin

**Riippuvuudet:** B3 valmis (STT Proxy toimii).

---

## 16. Acceptance criteria koko C-vaiheelle

C on valmis kun KAIKKI alla olevat ovat tosia:

1. `npm run build` rakentaa frontendin ilman virheitä
2. Frontend buildaa, deploydataan ja vibekoodausreitti `/vibe/:sessionId` avautuu publicista
3. Konseptinäkymässä "Aloita vibekoodaus" -nappi käynnistää session ja navigoi vibe-näkymään
4. Ensimmäinen prototyyppi näkyy iframessa session aloituksen jälkeen
5. Mobiilissa drawer avautuu/sulkeutuu sekä swipettämällä että klikkaamalla swipe-kahvaa
6. Desktopissa sidebar näkyy aina, ei drawer-käytöstä
7. Promptikenttään voi kirjoittaa, Päivitys-nappi lähettää pyynnön ja iframe päivittyy
8. Mode-toggle vaihtaa väriä ja lähettää oikean `mode`-arvon API:lle
9. Pohdinta-tilassa iframe ei muutu, vain Mestarin huomio -kenttä
10. Undo-nappi palauttaa edellisen version, disabled kun historiaa ei ole
11. Mikkinappula push-to-talk -logiikalla toimii Android Chromessa
12. Mikkinappula toimii iOS Safarissa (vähintään perustasolla)
13. STT-tulos asetetaan promptikenttään puheen jälkeen
14. Mikrofonioikeuden hylkääminen näyttää selkeän virheviestin
15. Pikatoimintojen painallus täyttää promptikentän valmiilla tekstillä
16. Concept drift -varoitus näkyy amber-tyylillä Mestarin huomio -kentässä
17. Sandbox expired -tilanteessa näytetään modal ja palautetaan konseptinäkymään
18. "📄 Konsepti" -painike topbarissa avaa modal-näkymän alkuperäisestä konseptista
19. Käännökset toimivat sekä fi että en kielillä
20. Esteettömyystestit menevät läpi (ARIA-labelit, tab-navigaatio, reduced motion)
21. Käsintestaus pienellä Android-puhelimella ei paljasta layout-ongelmia

---

## 17. Päätetyt asiat ja avoimet kysymykset

### 17.1 Päätetty (katselmoinnin 2026-05-28 perusteella)

1. **Pikatoiminnot lukittu** — neljä toimintoa: ✨ Vaihda tyyliä, 📱 Mobiilioptimoitu, 🔌 Lisää oikeaa dataa, ✂️ Yksinkertaista. Listaa voidaan laajentaa pilotin oppimisten perusteella.
2. **Drawer kiinni-tila 100px** — Mestarin huomio mahtuu kahdelle riville ilman tekstin leikkautumista.
3. **STT-kieli automaattinen** — i18n-asetuksen mukaan (fi → fi-FI, en → en-US). Ei käyttäjälle näkyvää kielivalintaa pilotissa.
4. **sessionStorage käytössä** — sandbox_id ja session-tila tallennetaan, sivun reload ei nollaa kokemusta.
5. **Konseptin näkyvyys** — topbariin lisätään "📄 Konsepti" -painike joka avaa modal-näkymän alkuperäisestä konseptista. Nuori voi milloin tahansa palata sanoihinsa.

### 17.2 Avoimet kysymykset toteutusta varten

Nämä eivät estä Codexin aloittamista, mutta hyvä päättää matkan varrella:

- **Pikatoimintojen mukautus tenanttikohtaisesti** — pitäisikö tenanttien (mina, maailma, jne.) tuottaa erilaisia pikatoimintoja vai pidetäänkö sama lista? Pilotissa: sama lista.
- **Sandboxin elinaika pidempänä pilotissa** — jos käyttötesteissä nuoret pitävät pidempiä taukoja, TTL voidaan kasvattaa 1h → 4h.
- **Konsepti-modalin sisältö** — näytetäänkö pelkkä Concept API:n konsepti vai myös Reveal-raportti? Ehdotus: ensisijaisesti konsepti, "Näytä myös alkuperäinen keskustelu" -linkki sen alle.

---

## 18. Liitteet ja viittaukset

- A-dokumentti: `kipina-vibe-A-konsepti.md`
- B-dokumentti: `kipina-vibe-B-backend.md`
- Rautalanka: `kipina-vibe-rautalanka.html` (chatissa 2026-05-28)
- Reveal Data API -frontend-integraatio: olemassa olevana Kipinä-frontendissä

---

*Loppu C-dokumentista. Suunnittelu valmis kommentoitavaksi.*
