# Kipinä Prototype API

B1-palvelu luo Mestarin avulla selainpohjaisia prototyyppejä konseptiraportista.

Nykyinen B1-valinta:

- Palvelu luo Agent Engine Code Execution -sandboxin istunnolle.
- Mestari tuottaa prototyypin HTML:n suoraan Gemini-vastauksena.
- Sandboxissa ei vielä ajeta HTML:ää tai JavaScriptiä. Tämä pidetään B1:ssä kevyenä, koska Template Proxy ja varsinainen validointivaihe tulevat myöhemmissä vaiheissa.

Tämä vastaa briefin kevyempää polkua: Agent Engine -kytkentä ja sandbox-elinkaari ovat mukana, mutta koodin suoritus syvennetään myöhemmin ilman julkisen HTTP-rajapinnan muutosta.

## Endpoints

- `GET /api/prototype/health`
- `POST /api/prototype/start`
- `POST /api/prototype/iterate`
- `POST /api/prototype/undo`
- `DELETE /api/prototype/{sandbox_id}`

Palvelu käynnistyy myös ilman GCP-resursseja, mutta prototype-endpointit palauttavat `503`, jos `AGENT_ENGINE_ID` tai service account -avain puuttuu.
