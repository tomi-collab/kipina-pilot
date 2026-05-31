# Kipinä Prototype API

B1-palvelu luo Mestarin avulla selainpohjaisia prototyyppejä konseptiraportista.

Nykyinen B1-valinta:

- Palvelu luo kevyen Kipinä-sandbox-tunnisteen istunnolle.
- Mestari tuottaa prototyypin HTML:n suoraan Gemini-vastauksena.
- Sandboxissa ei vielä ajeta HTML:ää tai JavaScriptiä. Tämä pidetään B1:ssä kevyenä, koska Template Proxy ja varsinainen validointivaihe tulevat myöhemmissä vaiheissa.

Tämä vastaa briefin kevyempää polkua: prototyyppi generoidaan HTML:nä ja
istuntoa seurataan Kipinän omalla sandbox-tunnisteella ilman Agent Engine
-sandboxin luontia.

## Endpoints

- `GET /api/prototype/health`
- `POST /api/prototype/start`
- `POST /api/prototype/iterate`
- `POST /api/prototype/undo`
- `DELETE /api/prototype/{sandbox_id}`

Palvelu käynnistyy myös ilman Agent Engine -resurssia. Prototype-endpointit
tarvitsevat edelleen Vertex AI / Gemini -käyttöön service account -avaimen.
