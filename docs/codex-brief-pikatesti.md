# Codex-brief: Kipinä Vibe — Pikatesti-tila (kehittäjätyökalu)

**Tausta:** Vibekoodausvaiheen testaaminen vaatii tällä hetkellä **täyden Reveal-keskustelun ajamisen** (15–30 min) ennen kuin pääsee testaamaan Mestaria selaimessa. Tämä hidastaa Mestarin Instructions-säätöjen testausta merkittävästi.

B1:ssä Codex lisäsi Prototype API:n `/start`-endpointtiin tuen `vibe`-kentälle: jos `concept` ja `report` puuttuvat, `vibe` toimii niiden korvaajana. Tätä ei ole vielä kytketty frontendiin.

Tämä brief lisää **pienen kehittäjätyökalun** Kipinän etusivulle, jolla voi käynnistää vibekoodausistunnon suoraan ilman Reveal-vaihetta.

**Scope:**

- Etusivulle lisätään "🚀 Pikatesti" -painike
- Painike on **näkyvissä vain kehitysympäristössä** tai kun pääsykoodi on `superadmin`-avain (yksinkertaisin: `import.meta.env.DEV` -tarkistus tai erityinen URL-parametri `?pikatesti=1`)
- Painikkeen klikkaus avaa modal-näkymän jossa on yksi tekstikenttä ja "Aloita" -nappi
- Submit kutsuu `POST /api/prototype/start` lähettäen vain `session_id` ja `vibe`, ja navigoi `/vibe/:sessionId`-reittiin
- VibeStudioView käsittelee sandbox-vastauksen normaalisti — ei muita muutoksia

---

## 1. Tiedostot jotka luodaan tai muutetaan

**Luotavat:**
- `src/components/PikatestiModal.tsx` — modaalikomponentti
- `src/locales/fi/pikatesti.ts` — käännökset
- `src/locales/en/pikatesti.ts` — käännökset

**Muutettavat:**
- Etusivun komponentti (todennäköisesti `src/views/HomeView.tsx` tai vastaava — etsi pääsykoodi-näkymä)
- `src/api/vibeApi.ts` — laajennetaan `startPrototype`-funktion typescript-tyyppejä sallimaan `vibe`-kenttä

---

## 2. PikatestiModal.tsx

```tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { startPrototype } from '../api/vibeApi';

interface PikatestiModalProps {
  open: boolean;
  onClose: () => void;
}

export function PikatestiModal({ open, onClose }: PikatestiModalProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [vibe, setVibe] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!vibe.trim()) return;
    setIsLoading(true);
    setError(null);
    const sessionId = `pikatesti-${Date.now()}`;
    try {
      const response = await startPrototype({
        sessionId,
        vibe: vibe.trim()
      });
      // Tallenna sandbox + alustava HTML sessionStorageen jotta VibeStudioView löytää ne
      sessionStorage.setItem(`kipina-vibe-${sessionId}`, JSON.stringify({
        sandboxId: response.sandbox_id,
        prototypeHtml: response.prototype_html,
        mestariMessage: response.mestari_message,
        iterationCount: 0
      }));
      navigate(`/vibe/${sessionId}`);
    } catch (err) {
      setError(t('pikatesti.errors.startFailed'));
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-emerald-400">
            {t('pikatesti.title')}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100"
            aria-label={t('pikatesti.close')}
          >
            ✕
          </button>
        </div>

        <p className="text-sm text-slate-400">
          {t('pikatesti.description')}
        </p>

        <textarea
          className="w-full bg-slate-800 border border-slate-700 rounded-2xl p-4
                     text-sm text-slate-100 focus:ring-2 focus:ring-emerald-500
                     focus:border-transparent outline-none transition-all
                     h-32 resize-none"
          placeholder={t('pikatesti.placeholder')}
          value={vibe}
          onChange={e => setVibe(e.target.value)}
          disabled={isLoading}
          autoFocus
        />

        {error && (
          <p className="text-sm text-rose-400">{error}</p>
        )}

        <div className="flex gap-2">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-100
                       font-semibold py-3 rounded-2xl transition-all
                       disabled:opacity-50"
          >
            {t('pikatesti.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !vibe.trim()}
            className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950
                       font-bold py-3 rounded-2xl shadow-[0_0_20px_rgba(16,185,129,0.3)]
                       transition-all transform active:scale-95
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? t('pikatesti.loading') : t('pikatesti.start')}
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## 3. Etusivun muutos

Etsi etusivun komponentti (todennäköisesti `HomeView.tsx` tai `IndexPage.tsx`). Lisää:

```tsx
import { useState } from 'react';
import { PikatestiModal } from '../components/PikatestiModal';

export function HomeView() {
  const [pikatestiOpen, setPikatestiOpen] = useState(false);
  const showPikatesti = import.meta.env.DEV ||
                        new URLSearchParams(window.location.search).get('pikatesti') === '1';

  return (
    <>
      {/* olemassa oleva sisältö */}

      {showPikatesti && (
        <button
          onClick={() => setPikatestiOpen(true)}
          className="fixed bottom-4 right-4 z-40
                     bg-emerald-500/20 hover:bg-emerald-500/40
                     border border-emerald-500/40
                     text-emerald-300 px-4 py-2 rounded-full
                     text-sm font-semibold backdrop-blur transition-all"
        >
          🚀 Pikatesti
        </button>
      )}

      <PikatestiModal
        open={pikatestiOpen}
        onClose={() => setPikatestiOpen(false)}
      />
    </>
  );
}
```

Painike on aina **fixed bottom-right** ja korostuu hieman, mutta ei häiritse etusivun pääkäyttöliittymää.

---

## 4. vibeApi.ts laajennus

Päivitä `startPrototype`-funktion typescript-tyypit:

```typescript
export interface StartRequest {
  sessionId: string;
  // Joko kaikki kolme:
  concept?: string;
  report?: string;
  tenantId?: string;
  // Tai vain vibe (pikatesti):
  vibe?: string;
}

export async function startPrototype(payload: StartRequest): Promise<StartResponse> {
  const body: any = { session_id: payload.sessionId };

  if (payload.vibe) {
    body.vibe = payload.vibe;
  } else {
    body.concept = payload.concept;
    body.report = payload.report;
    body.tenant_id = payload.tenantId;
  }

  const response = await fetch(`/api/prototype/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`start_failed_${response.status}`);
  return response.json();
}
```

Backend hyväksyy jo molemmat muodot (B1:n Codex teki tämän tuen).

---

## 5. Käännökset

**`src/locales/fi/pikatesti.ts`:**

```typescript
export const pikatestiFi = {
  title: 'Pikatesti Mestarille',
  description: 'Kirjoita lyhyt kuvaus sovelluksesta jonka haluat Mestarin rakentavan. Ohittaa Reveal-keskustelun ja konseptin.',
  placeholder: 'Esim. "Tee päätöspäiväkirja jossa voi syöttää kaksi vaihtoehtoa ja saada plussat/miinukset"',
  start: 'Aloita',
  cancel: 'Peruuta',
  close: 'Sulje',
  loading: 'Käynnistetään…',
  errors: {
    startFailed: 'Mestaria ei voitu käynnistää. Tarkista palvelu ja yritä uudelleen.'
  }
};
```

**`src/locales/en/pikatesti.ts`:**

```typescript
export const pikatestiEn = {
  title: 'Quick test for Mestari',
  description: 'Write a short description of the app you want Mestari to build. Bypasses Reveal conversation and concept.',
  placeholder: 'E.g. "Build a decision diary where I can enter two options and get pros and cons"',
  start: 'Start',
  cancel: 'Cancel',
  close: 'Close',
  loading: 'Starting…',
  errors: {
    startFailed: 'Could not start Mestari. Check the service and try again.'
  }
};
```

Rekisteröi nämä Kipinän i18n-konfiguraatioon `pikatesti`-namespacen alle.

---

## 6. Acceptance criteria

1. `npm run build` rakentaa frontendin ilman virheitä
2. Kun ajaa frontendin dev-tilassa (`npm run dev`), etusivun oikeassa alakulmassa näkyy "🚀 Pikatesti" -painike
3. Tuotantorakennuksessa painike ei näy ellei URL:ssa ole `?pikatesti=1`-parametria
4. Painikkeen klikkaus avaa modaalin jossa on tekstikenttä ja Aloita-nappi
5. Tekstin syöttäminen ja Aloita kutsuu `POST /api/prototype/start` `vibe`-kentällä
6. Onnistunut kutsu navigoi `/vibe/:sessionId`-reittiin ja VibeStudioView näyttää ensimmäisen prototyypin
7. Modaalin sulkeminen (✕, Peruuta, tai modaalin ulkopuolelle klikkaaminen) ei tee API-kutsua
8. Virheessä modaalissa näkyy virheviesti, käyttäjä voi yrittää uudelleen
9. Käännökset toimivat sekä fi että en

---

## 7. Mitä EI tehdä tässä briefissä

- Älä lisää modaalia mobile-specific drawer-logiikalla — modaali on yksinkertainen keskitetty näkymä joka toimii sekä mobiili- että desktop-koossa
- Älä rakenna superadmin-järjestelmää kunnolla — `import.meta.env.DEV || ?pikatesti=1` riittää pilotissa
- Älä muuta VibeStudioView'ta — se osaa jo käsitellä pre-loaded session-tilan sessionStoragesta

---

## 8. Viittaukset

- `apps/prototype-api/app.py` — `/start`-endpointin `vibe`-kentän käsittely (lisätty B1:n yhteydessä)
- `src/views/VibeStudioView.tsx` — sessio-tilan lataus sessionStoragesta on jo C1:ssä
- `src/api/vibeApi.ts` — laajennettava startPrototype-typescript-tyyppi

---

**Brief loppuu.** Tämä on pieni työ, arvio 30–60 minuuttia. Aloita lukemalla etusivun nykyinen komponentti ja `vibeApi.ts` jotta tiedät tarkat sijainnit ja olemassa olevan koodin tyylin.
