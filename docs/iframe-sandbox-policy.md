# Kipinä - prototyypin iframe-sandbox-politiikka

Mestarin tuottamat prototyypit ajetaan srcdoc-iframessa. Koska prototyypit
ovat LLM:n generoimaa, ennen ajoa tarkistamatonta koodia ja palvelu on
suunnattu alaikäisille, iframe rajataan tiukasti. Oletus on kielto.

## Sallittu

- allow-scripts - JS-toiminnallisuus (pakollinen)
- allow-forms - lomakkeet ja syöte (pakollinen)
- allow-modals - alert/confirm/prompt (perustoiminta)
- clipboard-write - kopiointi leikepöydälle (matala riski, selvä hyöty)
- fullscreen - koko näyttö, erit. pelit (matala riski)

## Kielletty ja miksi

- allow-same-origin - KRIITTINEN: yhdessä allow-scriptsin kanssa antaisi
  pääsyn Kipinän origin-kontekstiin (sessionStorage, evästeet). Ei koskaan.
- allow-top-navigation - voisi ohjata koko sovelluksen pois.
- allow-popups - ei tarvetta, ulkoisten ikkunoiden avaus.
- clipboard-read - leikepöydän luku, herkempi kuin kirjoitus, ei tarvetta.
- camera / microphone / geolocation / payment / usb / midi - korkea
  herkkyys alaikäisten palvelussa, ei tarvetta nykytoiminnoille.
  Kamera ja kuvan lisäys harkitaan erikseen, jos tarve syntyy.

## Muutosperiaate

Uutta ominaisuutta sallitaan vain jos:

1. sille on selvä käyttötarkoitus,
2. riski on matala,
3. se ei avaa pääsyä Kipinän omaan kontekstiin tai laitteen herkkiin
   resursseihin.

allow-same-origin ei tule mukaan missään tilanteessa allow-scriptsin kanssa.
