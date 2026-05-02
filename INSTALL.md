# Kipinä v1 — Asennusohje

Tämä ohje vie Kipinä-pilotin frontend v1:n paikallisesta repostasi
`C:/dev/kipina-pilot` palvelimelle `pilot.kipina.digiter.fi` ja varmistaa
että kaikki toimii.

---

## Tiedostojen sijoittaminen

Pura `kipina-frontend.zip` ja siirrä sisältö repon kansioon.

| Lähde (zip-paketista) | Kohde repossasi |
|----------------------|-----------------|
| `kipina-frontend/` koko sisältö | `apps/frontend/` |
| `reveal-data-api-app.py` | `apps/reveal-data-api/app.py` (KORVAA nykyinen) |
| `docker-compose.snippet.yml` | yhdistä manuaalisesti `docker-compose.yml`:ään |
| `env.example.additions.txt` | lisää rivit `.env.example`-tiedostoon |

> **Tärkeä:** `docker-compose.snippet.yml` on ehdotus, ei suora korvaaja.
> Tämä siksi että minulla ei ole nykyistä `docker-compose.yml`:ää näkyvissä.
> Vertaa ja yhdistä manuaalisesti niin että säilytät olemassa olevat
> säädöt (esim. networks, volumes, restart-policyt joita ei snippetissä ole).

---

## Vaihe 1: Paikallinen testaus (valinnainen mutta suositeltava)

```bash
cd C:/dev/kipina-pilot/apps/frontend
npm install
npm run typecheck
npm run build
```

Jos kaikki onnistuu, voit committoida.

---

## Vaihe 2: Committointi ja push

```bash
cd C:/dev/kipina-pilot

# Lisää uudet tiedostot
git add apps/frontend/
git add apps/reveal-data-api/app.py
git add docker-compose.yml
git add .env.example

# Committoi (älä committaa .env tai secrets/)
git commit -m "Add frontend v1: login + 4 tenant pages, Reveal Engine proxy"

# Yhdistä GitHub-remote (tehdään kerran)
git remote add origin https://github.com/tomi-collab/kipina-pilot.git
git branch -M main
git push -u origin main
```

---

## Vaihe 3: Deploy palvelimelle

SSH palvelimelle ja vedä uusin koodi:

```bash
ssh pilot.kipina.digiter.fi

# Mene Kipinä-repoon (sijainti riippuu siitä, mihin se on kloonattu —
# todennäköisesti /opt/kipina-pilot tai vastaava)
cd /opt/kipina-pilot   # tai jossakin muualla — tarkista omat polut

# Hae uusin koodi
git pull origin main
```

### Aseta env-muuttujat palvelimella

Älä committaa todellisia arvoja. Aseta ne palvelimen `.env`-tiedostoon
docker-compose.yml:n vieressä:

```bash
# Palvelimella, repon juuressa
cat > .env <<'EOF'
KIPINA_ACCESS_CODE=valitse-vahva-koodi-tähän
REVEAL_ENGINE_BASE_URL=https://reveal-api-kanavana-XXXXX-lz.a.run.app
REVEAL_ENGINE_TENANT_KEY=oikea-tenant-key
REVEAL_ENGINE_API_KEY=oikea-api-key
REVEAL_ENGINE_TIMEOUT_SECONDS=60
EOF

chmod 600 .env
```

> Vahvista että `.env` on listattu `.gitignore`:ssa — kontekstidokumentin
> mukaan se on, mutta tarkista varmuuden vuoksi: `git check-ignore .env`
> pitäisi tulostaa `.env` jos kaikki on kunnossa.

### Buildaa ja käynnistä

```bash
# Pysäytä vanha kipina-hello (jos vielä pyörii) ja buildaa kaikki uudelleen
docker compose down
docker compose build kipina-frontend kipina-reveal-data-api
docker compose up -d

# Tarkista että molemmat ovat ylhäällä
docker compose ps
```

---

## Vaihe 4: Smoke test

```bash
# Health check edelleen toimii
curl http://localhost:8081/api/health
# → {"ok": true, "service": "reveal-data-api", "environment": "kipina-pilot"}

# Auth: väärä koodi → 401
curl -X POST http://localhost:8081/api/auth/check \
  -H 'Content-Type: application/json' \
  -d '{"code": "väärä"}'
# → {"ok": false}, status 401

# Auth: oikea koodi → 200
curl -X POST http://localhost:8081/api/auth/check \
  -H 'Content-Type: application/json' \
  -d "{\"code\": \"$(grep KIPINA_ACCESS_CODE .env | cut -d= -f2)\"}"
# → {"ok": true}, status 200

# Frontend serveeraa index.html
curl -I http://localhost:8080/
# → 200 OK, content-type: text/html

# Reveal Engine -proxy (valinnainen, käyttää oikeasti API-kiintiötä)
curl -X POST http://localhost:8081/api/idea \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "test-123", "message": "Haluaisin sovelluksen joka muistuttaa lääkkeistä."}'
# → {"reply": "...", "session_id": "test-123", "turn": 1, "finished": false, "report": null}
```

---

## Vaihe 5: Selaintesti

Avaa selaimessa: `https://pilot.kipina.digiter.fi`

Pitäisi nähdä:
1. Kipinä-yläpalkki + kielenvaihto FI/EN
2. "Tervetuloa Kipinään" -kortti pääsykoodikentällä
3. Syötä oikea koodi → siirtyy etusivulle (`/koti`)
4. "Aloita" → siirtyy idea-näkymään
5. Kirjoita idea → "Lähetä" → tekoälyn vastaus tulee
6. Kun keskustelu päättyy (`finished: true`), "Näytä konsepti" → konsepti-näkymä
7. "Tee prototyyppi" → placeholder-näkymä

---

## Tunnetut rajoitukset v1:ssä

- **Pääsykoodi**: yksi jaettu koodi kaikille. Vaihda ennen julkista lanseerausta.
- **Sessio sessionStoragessa**: jos käyttäjä sulkee selaimen, kirjautuminen
  ja keskustelu nollautuvat. Tarkoituksellinen valinta v1:ssä.
- **DLP**: ei vielä toteutettu proxyssa. Lisää `_handle_idea`:n alkuun
  ennen kuin pilotti laajenee oikeisiin käyttäjiin. Lähde Lomaketulkin
  DLP-suodatuksesta.
- **Vain 2 kieltä**: fi ja en. Lisätään ukraina, arabia, farsi v2:ssa.
- **Prototyyppi-näkymä**: placeholder. Vibe-koodaus -integraatio v2:ssa.
- **Ei tallennusta**: keskusteluja ei vielä tallenneta PostgreSQL:ään
  (Valkey + Postgres ovat docker-compose-stubbeja, ei vielä päällä).

---

## Jos jokin menee pieleen

**`docker compose build` epäonnistuu npm install -kohdassa:**
Tarkista että palvelimella on internet-yhteys (`curl -I https://registry.npmjs.org`).
Jos firewall blokkaa, lisää `--network host` build-aikaiseksi.

**Frontend renderöityy mutta `/api/auth/check` palauttaa 404:**
Caddyn reititys ei ole linjassa. Tarkista `infra/caddy/Caddyfile` — sen
pitäisi reitittää `/api/*` → `localhost:8081`. Reload: `sudo systemctl reload caddy`.

**`/api/idea` palauttaa 503 `engine_not_configured`:**
Env-muuttujat eivät päässeet containeriin. Tarkista `docker compose config`
ja että `.env` on samassa kansiossa kuin `docker-compose.yml`.

**`/api/idea` palauttaa 504 `engine_timeout`:**
Cloud Run kestää yli 60 sekuntia. Nosta `REVEAL_ENGINE_TIMEOUT_SECONDS`
arvoon 120 ja restart: `docker compose up -d kipina-reveal-data-api`.

**Selain näyttää vanhan välimuistitetun version:**
Tee hard reload (Ctrl+Shift+R). nginx.conf asettaa `Cache-Control: no-cache`
HTML:lle ja `immutable` hashattyille asseteille, joten tämän pitäisi olla
ongelma vain ensimmäisellä deploy-kerralla.
