# Kipinä Frontend (v1)

Kipinä pilotin käyttöliittymä. React 18 + Vite + TanStack Router + TanStack Query + Tailwind v4 + omat shadcn-tyyliset komponentit.

## Sivut

| Reitti | Sivu | Tarkoitus |
|--------|------|-----------|
| `/` | Login | Pääsykoodin syöttö |
| `/koti` | Home | Etusivu kirjautumisen jälkeen |
| `/idea` | Idea | Chat-tyylinen keskustelu Reveal Enginen kanssa |
| `/konsepti/:id` | Concept | Valmis konsepti (Reveal Enginen `report`) |
| `/proto/:id` | Prototype | Placeholder, valmiimpi v2:ssa |

## Vaadittavat ympäristömuuttujat

Frontend itse ei tarvitse ympäristömuuttujia. Kaikki konfiguraatio on reveal-data-API:ssa:

- `KIPINA_ACCESS_CODE` — jaettu pääsykoodi
- `REVEAL_ENGINE_BASE_URL` — Cloud Run URL
- `REVEAL_ENGINE_TENANT_KEY`
- `REVEAL_ENGINE_API_KEY`
- `REVEAL_ENGINE_TIMEOUT_SECONDS` (oletus 60)

## Kehitys paikallisesti

```bash
cd apps/frontend
npm install
npm run dev
```

Vite käynnistää devserverin osoitteessa `http://localhost:5173`. Pyynnöt
`/api/*` proxytetään `http://localhost:8081` (reveal-data-API).

Edellytys: reveal-data-API ajossa portissa 8081, env-muuttujat asetettuna.

## Tuotantobuild

```bash
docker compose build kipina-frontend
docker compose up -d kipina-frontend
```

Container kuuntelee `127.0.0.1:8080`. Caddy reitittää
`pilot.kipina.digiter.fi` → `127.0.0.1:8080` muutoksitta.

## Suunnitteluperiaatteet

Kohderyhmä: nuoret, maahanmuuttajat, seniorit ja henkilöt joilla on
kommunikaatio- tai toimintahaasteita.

- Kosketuspinnat ≥ 48×48 px (button.size = "lg" oletuksena, "xl" päätoiminnoille)
- AAA-kontrasti (foreground `#f5f7fa` taustaa `#101418` vasten = ~16:1)
- Yksi pääasiallinen toiminto per näkymä
- Selkokielinen virheviesti (ei "Error 500" — vaan "Yhteys katkesi.")
- Kielenvaihto näkyvissä joka sivulla yläpalkissa
- `prefers-reduced-motion` huomioitu
- Ei autoplayä, ei hover-only-interaktioita

## Mitä EI ole vielä

- i18n-frameworkki (yksinkertainen kieliobjekti riittää 2 kielelle, vaihto
  react-i18nextiin on helppo myöhemmin)
- DLP frontendin puolella (DLP tehdään palvelimella ennen Cloud Run -kutsua)
- Prototyyppi-näkymän todellinen sisältö (placeholder v1:ssä)
- Komponenttitestit (ei aikaa demoon)
