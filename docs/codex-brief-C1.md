# Codex-brief: Kipinä Vibe — C1. VibeStudioView ja perustoiminta

**Tausta:** Kipinä Vibe -putken backend B1 on toiminnassa: Prototype API kutsuu Vertex AI Agent Engineä ja Mestari tuottaa selainprototyyppejä. Nyt rakennetaan ensimmäinen vaihe frontendista, jolla nuori pääsee oikeasti kokemaan vibekoodausvaiheen.

**Scope C1:n osalta:**

C1 = perustoiminta. Mukana:
- Uusi reitti `/vibe/:sessionId`
- VibeStudioView pääkomponentti
- Prototyypin iframe live preview
- Promptikentän kautta tekstillä lähetettävät iteraatiot Koodaus-tilassa
- Drawer mobiilissa, sidebar desktopissa
- Vasemman alakulman "Aloita vibekoodaus" -nappi konseptinäkymässä
- Käännösavaimet `vibe.*`

**EI mukana C1:ssä** (tulee C2:ssa ja C3:ssa):
- Mode-toggle (Koodaus/Pohdinta) → C2
- Undo-nappi → C2
- Mestarin huomio -kenttä konseptidrift-tyylillä → C2
- Pikatoimintonapit → C2
- VibeConceptModal ja VibeHistoryModal → C2
- VibeSuggestionPanel (Mestari-Suosittelija) → C2
- Mikkinappula ja STT → C3

C1 tuottaa toimivan vibekoodauskokemuksen tekstillä — mobiilikäyttäjä voi kirjoittaa promptin, painaa Päivitys, ja nähdä prototyypin muuttuvan. Kaikki muu rakennetaan tämän päälle myöhemmissä vaiheissa.

**Suunnitteluperiaate: mobile-first.** Mobiililayout on default, desktop-versio on poikkeus johon lisätään tilaa. Lähde 380px viewportista ja lisää tila `md:`-breakpointissa.

---

## 1. Tiedostot jotka luodaan

```
src/views/VibeStudioView.tsx              # Pääkomponentti, route /vibe/:sessionId
src/components/vibe/VibePreview.tsx       # Iframe live preview
src/components/vibe/VibeControls.tsx      # Kontrollipaneeli (textarea + Päivitys-nappi)
src/components/vibe/VibeDrawer.tsx        # Mobiilin liukupaneeli
src/hooks/useVibeSession.ts               # Tilankäsittely + API-kutsut
src/api/vibeApi.ts                        # Prototype API:n kutsujen kääre
src/locales/fi/vibe.ts                    # Suomenkieliset käännökset (vibe-osio)
src/locales/en/vibe.ts                    # Englanninkieliset käännökset
```

Muutokset olemassa oleviin tiedostoihin:
- React Router -konfiguraatio (uusi reitti `/vibe/:sessionId`)
- Konseptinäkymän komponentti (lisätään "Aloita vibekoodaus" -nappi)
- i18n-konfiguraatio (rekisteröidään uudet käännöstiedostot)

---

## 2. Reititys

Lisää React Routeriin uusi reitti pääsykoodi-suojauksen alle:

```tsx
<Route path="/vibe/:sessionId" element={
  <RequireAccessCode>
    <VibeStudioView />
  </RequireAccessCode>
} />
```

`sessionId` luetaan URL-parametrista. Jos se puuttuu tai on virheellisen muotoinen, redirectoi etusivulle.

---

## 3. VibeStudioView — pääkomponentti

### 3.1 Layout

Mobiililayout (default, < 768px):

```
┌─────────────────────────────────┐
│ ← Takaisin                      │ ← topbar 56px
├─────────────────────────────────┤
│                                 │
│                                 │
│       <iframe srcdoc=...>       │ ← VibePreview
│                                 │
│                                 │
├─────────────────────────────────┤
│  ───  (swipe-kahva)             │ ← VibeDrawer, kiinni 100px
│  Pyydä Mestaria muuttamaan       │
└─────────────────────────────────┘
```

Drawer auki:

```
┌─────────────────────────────────┐
│ ← Takaisin                      │
├─────────────────────────────────┤
│       <iframe srcdoc=...>       │ ← Preview puristettu
├─────────────────────────────────┤
│ ───                             │
│ NUOREN VIBE / OHJE              │
│ ┌─────────────────────────────┐ │
│ │ Mitä muutetaan?             │ │ ← textarea
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│         [ PÄIVITYS ]            │ ← iso vihreä nappi
└─────────────────────────────────┘
```

Desktop-layout (≥ 768px):

Kaksi pystysaraketta, vasemmalla sidebar (kontrollipaneeli, 320–384px leveä, aina näkyvissä), oikealla iframe.

### 3.2 Tilanhallinta

VibeStudioView käyttää `useVibeSession`-hookia (ks. luku 7).

Tila:

```typescript
interface VibeSessionState {
  sandboxId: string | null;
  sessionId: string;
  prototypeHtml: string;
  mestariMessage: string;
  iterationCount: number;
  drawerOpen: boolean;    // mobiili
  isLoading: boolean;
  promptText: string;
  error: string | null;
}
```

### 3.3 Alustus

Mountatessa:
1. Tarkista onko `sessionStorage`-avaimessa `kipina-vibe-{sessionId}` aiempaa session-tilaa
2. Jos on (esim. sivun reload), palauta tila: sandboxId, viimeisin prototypeHtml, iterationCount
3. Jos ei, kutsu `POST /api/prototype/start` URL:n `sessionId`:llä. Tarvitaan konsepti ja raportti — luetaan ne `sessionStorage`-avaimista jotka konseptinäkymä on tallentanut (`kipina-concept-{sessionId}` ja `kipina-report-{sessionId}`).
4. Tallenna palautettu sandboxId, prototypeHtml, mestariMessage tilaan ja `sessionStorage`en.

Virheessä `start` palauttaa 502 → näytä virheviesti modal-muodossa "Vibekoodausta ei voitu aloittaa. Yritä uudelleen.".

---

## 4. VibePreview — iframe live preview

```tsx
<iframe
  className="w-full h-full border-none"
  srcDoc={prototypeHtml}
  sandbox="allow-scripts"
  title="Prototyyppi"
/>
```

**Sandbox-attribuutti `allow-scripts`** — sallii JS:n iframessa, mutta estää pääsyn Kipinän cookieihin, lomakkeisiin, pop-uppeihin ja sivun uudelleenohjaukseen.

**Lataustila:** kun `isLoading=true`, iframen päälle näytetään puolikvint peittokerros (`bg-slate-900/60`) jossa keskellä pyörivä spinneri ja teksti "Mestari koodaa…" (käännös `vibe.preparing`). Vanha versio jää alle näkyväksi.

---

## 5. VibeControls — kontrollipaneeli

### 5.1 Promptikenttä

```tsx
<textarea
  className="w-full bg-slate-800 border border-slate-700 rounded-2xl p-4
             text-sm text-slate-100 focus:ring-2 focus:ring-emerald-500
             focus:border-transparent outline-none transition-all
             h-24 md:h-32 resize-none"
  placeholder={t('vibe.promptPlaceholder')}
  value={promptText}
  onChange={e => setPromptText(e.target.value)}
  disabled={isLoading}
/>
```

### 5.2 Päivitys-nappi

```tsx
<button
  className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950
             font-bold py-4 rounded-2xl mt-4
             shadow-[0_0_20px_rgba(16,185,129,0.3)]
             transition-all transform active:scale-95
             disabled:opacity-50 disabled:cursor-not-allowed"
  onClick={handleSubmit}
  disabled={isLoading || !promptText.trim()}
>
  {isLoading ? t('vibe.updating') : t('vibe.update')}
</button>
```

Painallus laukaisee `handleSubmit`:
1. Trimmaa `promptText`
2. Kutsuu `iteratePrototype({sandboxId, mode: 'koodaus', userInput: trimmedText, language: currentLanguage})`
3. Onnistuessa: päivittää `prototypeHtml`, `mestariMessage`, `iterationCount` tilaan ja sessionStorageen, tyhjentää `promptText`
4. Virheessä: näyttää virheviestin toast-tyyppisesti, ei tyhjennä `promptText`

C1:ssä `mode` on aina `koodaus` (kovakoodattu). C2:ssa lisätään mode-toggle.

---

## 6. VibeDrawer — mobiilin liukupaneeli

### 6.1 CSS

```css
.drawer {
  transform: translateY(calc(100% - 100px));
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer.open {
  transform: translateY(0);
}
@media (prefers-reduced-motion: reduce) {
  .drawer { transition: none; }
}
@media (min-width: 768px) {
  .drawer { transform: none !important; position: static; }
}
```

### 6.2 Drawer-toiminta mobiilissa

```typescript
const drawerHeaderRef = useRef<HTMLDivElement>(null);
const [startY, setStartY] = useState(0);

useEffect(() => {
  const el = drawerHeaderRef.current;
  if (!el) return;

  const onTouchStart = (e: TouchEvent) => setStartY(e.touches[0].clientY);
  const onTouchEnd = (e: TouchEvent) => {
    const endY = e.changedTouches[0].clientY;
    const diff = endY - startY;
    if (diff > 30) setDrawerOpen(false);
    else if (diff < -30) setDrawerOpen(true);
    else if (Math.abs(diff) < 10) setDrawerOpen(prev => !prev);
  };

  el.addEventListener('touchstart', onTouchStart, { passive: true });
  el.addEventListener('touchend', onTouchEnd, { passive: true });
  return () => {
    el.removeEventListener('touchstart', onTouchStart);
    el.removeEventListener('touchend', onTouchEnd);
  };
}, [startY]);
```

Swipe-kahva on drawerin yläosa (50px korkea kosketus-alue), johon kuuluu visuaalinen kahvaviiva ("───") ja Mestarin huomio -kenttä (C2:ssa, C1:ssä jätetään pelkkä kahvaviiva).

Klikkaus drawer-kahvaan toggles drawer-tilan. Klikkaus iframen päällä EI vaikuta drawer-tilaan.

---

## 7. useVibeSession-hook

```typescript
function useVibeSession(sessionId: string) {
  const [state, dispatch] = useReducer(vibeReducer, initialState);

  const startSession = async (concept: string, report: string, tenantId: string) => {
    dispatch({ type: 'START_BEGIN' });
    try {
      const response = await startPrototype({ concept, report, tenantId, sessionId });
      dispatch({ type: 'START_SUCCESS', payload: response });
      saveToSessionStorage(sessionId, response);
    } catch (err) {
      dispatch({ type: 'START_ERROR', payload: err.message });
    }
  };

  const iterate = async (input: string) => {
    if (!state.sandboxId) return;
    dispatch({ type: 'ITERATE_BEGIN' });
    try {
      const response = await iteratePrototype({
        sandboxId: state.sandboxId,
        mode: 'koodaus',
        userInput: input,
        language: currentLanguage()
      });
      dispatch({ type: 'ITERATE_SUCCESS', payload: response });
      saveToSessionStorage(sessionId, { ...state, ...response });
    } catch (err) {
      dispatch({ type: 'ITERATE_ERROR', payload: err.message });
    }
  };

  const setPromptText = (text: string) => dispatch({ type: 'SET_PROMPT', payload: text });
  const toggleDrawer = () => dispatch({ type: 'TOGGLE_DRAWER' });

  return { state, startSession, iterate, setPromptText, toggleDrawer };
}
```

**SessionStorage-avaimet:**
- `kipina-vibe-{sessionId}` — koko VibeSessionState (paitsi UI-tila kuten `drawerOpen`)
- `kipina-concept-{sessionId}` — konsepti (luetaan, ei kirjoiteta tässä)
- `kipina-report-{sessionId}` — raportti (luetaan, ei kirjoiteta tässä)

Sivun reload palauttaa tilan sessionStoragesta — nuori voi jatkaa siitä mihin jäi (paitsi jos sandbox TTL umpeutui, jolloin seuraava iterate-kutsu palauttaa 404 → näytä modal "Sessio päättyi, aloita uusi vibekoodaus" → ohjaa konseptinäkymään).

---

## 8. vibeApi.ts — API-kutsujen kääre

```typescript
const BASE = '/api/prototype';

export interface StartRequest {
  concept: string;
  report: string;
  tenantId: string;
  sessionId: string;
}

export interface StartResponse {
  sandbox_id: string;
  prototype_html: string;
  mestari_message: string;
  ttl_seconds: number;
}

export async function startPrototype(payload: StartRequest): Promise<StartResponse> {
  const response = await fetch(`${BASE}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      concept: payload.concept,
      report: payload.report,
      tenant_id: payload.tenantId,
      session_id: payload.sessionId
    })
  });
  if (!response.ok) throw new Error(`start_failed_${response.status}`);
  return response.json();
}

export interface IterateRequest {
  sandboxId: string;
  mode: 'koodaus' | 'pohdinta';
  userInput: string;
  language: 'fi' | 'en';
}

export interface IterateResponse {
  prototype_html?: string;
  mestari_message: string;
  iteration_count: number;
  concept_drift_warning?: string | null;
}

export async function iteratePrototype(payload: IterateRequest): Promise<IterateResponse> {
  const response = await fetch(`${BASE}/iterate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sandbox_id: payload.sandboxId,
      mode: payload.mode,
      user_input: payload.userInput,
      language: payload.language
    })
  });
  if (response.status === 404) throw new Error('sandbox_not_found');
  if (!response.ok) throw new Error(`iterate_failed_${response.status}`);
  return response.json();
}
```

C1:ssä tarvitaan vain `startPrototype` ja `iteratePrototype`. Muut endpointit (`undo`, `history`, `suggest-iteration`, `DELETE`) kytketään C2:ssa.

---

## 9. Käännösavaimet

`src/locales/fi/vibe.ts`:

```typescript
export const vibeFi = {
  startButton: 'Aloita vibekoodaus',
  startLoading: 'Mestari valmistelee ensimmäistä versiota…',
  preparing: 'Mestari koodaa…',
  update: 'PÄIVITYS',
  updating: 'Päivitetään…',
  back: 'Takaisin',
  promptPlaceholder: 'Mitä muutetaan? Esim. "Tee tästä neonvihreä"',
  errors: {
    sessionExpired: 'Sessio päättyi. Aloita uusi vibekoodaus.',
    sessionExpiredAction: 'Aloita uudelleen',
    networkError: 'Yhteys katkesi. Yritä uudelleen.',
    mestariNotResponding: 'Mestari ei juuri nyt vastaa. Yritä uudelleen.',
    startFailed: 'Vibekoodausta ei voitu aloittaa. Yritä uudelleen.'
  }
};
```

`src/locales/en/vibe.ts`:

```typescript
export const vibeEn = {
  startButton: 'Start vibe coding',
  startLoading: 'Mestari is preparing the first version…',
  preparing: 'Mestari is coding…',
  update: 'UPDATE',
  updating: 'Updating…',
  back: 'Back',
  promptPlaceholder: 'What to change? E.g. "Make this neon green"',
  errors: {
    sessionExpired: 'Session ended. Start a new vibe coding.',
    sessionExpiredAction: 'Start again',
    networkError: 'Connection lost. Try again.',
    mestariNotResponding: 'Mestari is not responding right now. Try again.',
    startFailed: 'Could not start vibe coding. Try again.'
  }
};
```

Rekisteröi nämä Kipinän olemassa olevaan i18n-konfiguraatioon `vibe`-namespace-avaimen alle. C2:ssa käännöstiedostoja täydennetään.

---

## 10. Konseptinäkymän päivitys

Etsi nykyinen konseptinäkymän komponentti (todennäköisesti `ConceptView.tsx` tai `ConceptPage.tsx`).

Korvaa nykyinen "Tee prototyyppi" -placeholdernappi (tai vastaava) seuraavalla:

```tsx
<button
  className="w-full md:w-auto bg-emerald-500 hover:bg-emerald-400
             text-slate-950 font-bold py-4 px-8 rounded-2xl mt-6
             shadow-[0_0_20px_rgba(16,185,129,0.3)]
             transition-all transform active:scale-95
             disabled:opacity-50"
  onClick={handleStartVibeCoding}
  disabled={!concept || !report}
>
  {t('vibe.startButton')}
</button>
```

`handleStartVibeCoding`:
1. Tallennetaan `sessionStorage`en konsepti ja raportti avaimilla `kipina-concept-{sessionId}` ja `kipina-report-{sessionId}`
2. Navigoidaan reittiin `/vibe/{sessionId}` (käytä `useNavigate()`-hookia)
3. VibeStudioView mountatessaan lukee nämä ja kutsuu `startPrototype`-API:ta

---

## 11. Värisuunnitelma ja tyyli

Kipinän nykyinen tumma teema säilyy:

- Tausta: `bg-slate-950`
- Paneelit: `bg-slate-900`, `border-slate-700`
- Koodaus-tilan korostusväri: `emerald-500` (vihreä)
- Teksti: `slate-100` (vaalea), `slate-400` (himmennetty)

Pyöristykset isohkot (`rounded-2xl` ja `rounded-3xl`), glow-tyyliset varjot Päivitys-napille.

Tailwind on käytössä Viten kautta — älä käytä Tailwind CDN:ää tuotannossa, vain build-pohjaista versiota. Jos `tailwind.config.js` ei ole projektissa, lisää se:

```javascript
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  theme: { extend: {} },
  plugins: []
};
```

---

## 12. Esteettömyys

- Topbarin Takaisin-napilla `aria-label={t('vibe.back')}`
- Promptikentällä `aria-label={t('vibe.promptPlaceholder')}`
- Päivitys-napilla teksti on suoraan käännöstiedostosta
- Drawer-kahvalle `role="button"` ja `aria-expanded={drawerOpen}`
- Tab-navigaatio: drawer-kahva → textarea → Päivitys-nappi
- Reduced motion: drawerin transition poistetaan

---

## 13. Mobile-testauksen tarkistuslista

Manuaalitestit oikealla puhelimella:

1. Android Chrome — avaa Kipinä, kirjaudu pääsykoodilla, suorita yksi tenant-keskustelu loppuun saakka, paina Aloita vibekoodaus
2. Vibekoodausnäkymä avautuu, iframessa näkyy Mestarin ensimmäinen prototyyppi
3. Drawer avautuu pyyhkäisemällä alhaalta ylös
4. Drawer sulkeutuu pyyhkäisemällä ylhäältä alas
5. Tekstikenttään voi kirjoittaa, näppäimistö ilmestyy, ei peitä tekstiä
6. Päivitys-nappi disabloi itsensä lähetyksen ajaksi, näyttää "Päivitetään…"
7. Iframe päivittyy uudella versiolla, prompt-kenttä tyhjenee
8. Sivun reload säilyttää session-tilan (sandboxId, viimeisin HTML)
9. iOS Safari — sama testitarkistus, erityisesti drawer-pyyhkäisy ja näppäimistö-käyttäytyminen

---

## 14. Acceptance criteria

C1 on valmis kun KAIKKI alla olevat ovat tosia:

1. `npm run build` rakentaa frontendin ilman virheitä
2. `/vibe/:sessionId`-reitti avautuu kun pääsykoodi on syötetty
3. Konseptinäkymässä "Aloita vibekoodaus" -nappi käynnistää session ja navigoi vibe-näkymään
4. Vibe-näkymä kutsuu `POST /api/prototype/start` ja näyttää ensimmäisen prototyypin iframessa
5. Promptikenttään voi kirjoittaa, Päivitys-nappi lähettää `POST /api/prototype/iterate` ja iframe päivittyy uudella versiolla
6. Mobiilissa drawer avautuu pyyhkäisemällä ja klikkaamalla swipe-kahvaa
7. Desktopissa (≥ 768px) sidebar näkyy aina, drawer-käyttäytyminen ei ole päällä
8. Sivun reload palauttaa session-tilan sessionStoragesta
9. Sandbox expired -tilanteessa (404 iterate-kutsussa) näytetään modal ja palautetaan konseptinäkymään
10. Käännökset toimivat sekä fi että en kielillä
11. Push-to-talk -mikkinappula EI ole vielä mukana — se on placeholderina tai puuttuu kokonaan paneelista (lisätään C3:ssa)
12. Mode-toggle ja undo-nappi EIVÄT ole mukana — ne lisätään C2:ssa
13. Käsintestaus oikealla Android-puhelimella ei paljasta layout-ongelmia

---

## 15. Mitä lipata Tomille ennen kuin edetään

Pyydä tarkennusta jos:

- Olemassa olevan konseptinäkymän komponentin nimi tai sijainti ei ole löydettävissä — tarvitaan tarkka polku
- i18n-konfiguraatio käyttää eri rakennetta kuin oletettu — millä mekanismilla uudet namespacet rekisteröidään?
- React Router -version syntaksi (`<Route path>`) tai konfiguraatio poikkeaa briefista
- Pääsykoodi-suojaus on toteutettu komponentilla jolla on eri nimi kuin `RequireAccessCode`

---

## 16. Mitä EI tehdä C1:ssä (myöhemmissä vaiheissa)

C2-vaiheessa lisätään:
- VibeModeToggle (Koodaus/Pohdinta -kytkin)
- Mestarin huomio -kenttä draweriin (Pohdinta-tilan vastaukset)
- Undo-nappi + undoPrototype-API-kutsu
- VibeQuickActions (4 pikatoimintoa)
- VibeConceptModal (Näytä konsepti -modal)
- VibeHistoryModal (Mitä mä äsken sanoin)
- VibeSuggestionPanel (Mestari-Suosittelija, vain superadmin)
- Concept drift -varoitus amber-tyylillä
- Topbar-painikkeet "📄 Konsepti" ja "🕓 Historia"

C3-vaiheessa lisätään:
- VibeMicButton (push-to-talk)
- useSpeechRecorder-hook
- STT Proxy -integraatio (vaatii backend B3:n valmiina)
- Mikkinappulan väri vaihtuu tilan mukaan

C1:ssä ei rakenneta näitä etukäteen — keskitytään pelkkään tekstipohjaiseen Koodaus-tilan iteraatioon. Pidetään komponenttirakenne sellaisena että lisäykset C2:ssa ja C3:ssa ovat helppoja (esim. VibeControls voi ottaa tulevaisuudessa vastaan props joilla aktivoidaan tilat).

---

## 17. Viittaukset

- C-dokumentti: `kipina-vibe-C-frontend.md` (täysi suunnitelma kaikille C-vaiheille)
- B1-toteutuksen API: `apps/prototype-api/app.py` (endpointit `/start` ja `/iterate` toimivat)
- Rautalanka: `kipina-vibe-rautalanka.html` (visuaalinen referenssi)

---

**Brief loppuu.** Aloita lukemalla olemassa oleva konseptinäkymä jotta löydät "Tee prototyyppi" -placeholdernapin paikan, ja seuraa Kipinän nykyistä komponenttitiedostojen tyyliä. Jos jokin yllä on epäselvää, pyydä tarkennusta ennen kuin arvaat.
