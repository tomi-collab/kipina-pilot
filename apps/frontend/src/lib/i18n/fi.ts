import { pikatestiFi } from '@/locales/fi/pikatesti'

export interface Translations {
  app: {
    title: string
    tagline: string
  }
  nav: {
    home: string
    logout: string
  }
  language: {
    label: string
    fi: string
    en: string
  }
  login: {
    heading: string
    description: string
    codeLabel: string
    codePlaceholder: string
    submit: string
    error: string
    networkError: string
  }
  home: {
    heading: string
    loadingTenants: string
    startButton: string
  }
  idea: {
    heading: string
    placeholder: string
    send: string
    sending: string
    networkError: string
    yourTurn: string
    assistantTurn: string
    finishedNotice: string
    showConcept: string
  }
  concept: {
    heading: string
    description: string
    generateButton: string
    loading: string
    errorTitle: string
    errorRetry: string
    generatedHeading: string
    nextStep: string
    backToHome: string
  }
  prototype: {
    heading: string
    description: string
    placeholder: string
    backToHome: string
  }
  vibe: {
    startButton: string
    startLoading: string
    preparing: string
    update: string
    updating: string
    back: string
    drawerLabel: string
    promptPlaceholder: string
    tips: string[]
    errors: {
      sessionExpired: string
      sessionExpiredAction: string
      networkError: string
      mestariNotResponding: string
      startFailed: string
    }
  }
  pikatesti: {
    title: string
    description: string
    placeholder: string
    start: string
    cancel: string
    close: string
    loading: string
    button: string
    errors: {
      startFailed: string
    }
  }
  common: {
    back: string
    loading: string
    retry: string
  }
}

export const fi: Translations = {
  app: {
    title: 'Kipinä',
    tagline: 'Emmä tiiä ei oo enää ihan sama',
  },
  nav: {
    home: 'Etusivu',
    logout: 'Kirjaudu ulos',
  },
  language: {
    label: 'Kieli',
    fi: 'Suomi',
    en: 'English',
  },
  login: {
    heading: 'Tervetuloa Kipinään',
    description:
      'Kerro arjen ideastasi tai haasteestasi. Tekoäly auttaa sinua viemään sen eteenpäin.',
    codeLabel: 'Pääsykoodi',
    codePlaceholder: 'Syötä koodi',
    submit: 'Aloita',
    error: 'Pääsykoodi ei ole oikein.',
    networkError: 'Yhteys katkesi. Yritä uudelleen.',
  },
  home: {
    heading: 'Mistä kerrot tänään?',
    loadingTenants: 'Ladataan...',
    startButton: 'Aloita',
  },
  idea: {
    heading: 'Kerro ideastasi',
    placeholder:
      'Kerro omin sanoin, mitä mieleesi tuli. Esimerkiksi: "Haluaisin sovelluksen, joka..."',
    send: 'Lähetä',
    sending: 'Tekoäly miettii...',
    networkError: 'Yhteys katkesi. Yritä uudelleen.',
    yourTurn: 'Sinun vuorosi',
    assistantTurn: 'Tekoäly',
    finishedNotice: 'Konsepti on valmis!',
    showConcept: 'Näytä konsepti',
  },
  concept: {
    heading: 'Konseptisi',
    description: 'Tekoäly muotoili ideastasi seuraavan konseptin:',
    generateButton: 'Luo konsepti',
    loading: 'Luodaan konseptia...',
    errorTitle: 'Konseptin luonti epäonnistui',
    errorRetry: 'Yritä uudelleen',
    generatedHeading: 'Konsepti',
    nextStep: 'Tee prototyyppi',
    backToHome: 'Etusivulle',
  },
  prototype: {
    heading: 'Prototyyppisi',
    description:
      'Tästä syntyy seuraavaksi toimiva prototyyppi tekoälyn avulla.',
    placeholder:
      'Tämä osio on rakenteilla. Valmiissa pilotissa näet tästä toimivan rautalankamallin ideastasi.',
    backToHome: 'Etusivulle',
  },
  vibe: {
    startButton: 'Aloita vibekoodaus',
    startLoading: 'Mestari valmistelee ensimmäistä versiota...',
    preparing: 'Mestari koodaa...',
    update: 'PÄIVITYS',
    updating: 'Päivitetään...',
    back: 'Takaisin',
    drawerLabel: 'Pyydä Mestaria muuttamaan',
    promptPlaceholder:
      'Pyydä muutosta tai kysy mitä vain — esim. "tee napista isompi" tai "miksei tää toimi?"',
    tips: [
      'Voit pyytää Mestaria tarkasti: "tee napista isompi" toimii paremmin kuin "tee siitä kivempi".',
      'Mitä selkeämmin kerrot mitä haluat, sitä lähemmäs Mestari osuu.',
      '"Siirrä otsikko keskelle" on Mestarille helpompi kuin "korjaa toi yläosa".',
      'Jos jokin ei mene niin kuin halusit, sano vielä tarkemmin mitä tarkoitit.',
      'Yksi muutos kerrallaan on usein helpompi kuin monta yhtä aikaa.',
      'Et tykkää väristä? Sano vaikka "vaihda tausta tummaksi" — Mestari hoitaa.',
      'Voit pyytää Mestaria kokeilemaan toisia värejä, jos ekana ei napannut.',
      '"Tee tästä värikkäämpi" tai "rauhallisemman näköinen" — Mestari ymmärtää fiiliksenkin.',
      'Voit pyytää isompaa tekstiä, jos jotain on hankala lukea.',
      'Haluatko pyöreämmät nurkat tai isommat napit? Pyydä vaan.',
      'Voit pyytää Mestaria vaihtamaan minkä tahansa tekstin toiseksi.',
      '"Vaihda otsikoksi…" — kerro mitä haluat lukevan, niin se vaihtuu.',
      'Jos jokin sana tuntuu väärältä, sano Mestarille uusi.',
      'Voit pyytää Mestaria lisäämään uuden napin, kentän tai osion.',
      '"Laita napit allekkain" tai "vieretysten" — asettelua voi muuttaa pyytämällä.',
      'Jos jokin on väärässä paikassa, kerro mihin haluat sen.',
      'Voit pyytää lisää tilaa elementtien väliin, jos näyttää ahtaalta.',
      'Meni liian pitkälle? Voit aina perua viimeisen muutoksen.',
      'Uskalla kokeilla — jos et tykkää, voit perua ja yrittää toisin.',
      'Mikään ei mene rikki kokeilemalla. Aina voi palata taaksepäin.',
      'Jos uusi versio oli huonompi kuin edellinen, peru se vaan.',
      'Voit myös vain kysyä Mestarilta neuvoa — ei pakko pyytää muutosta joka kerta.',
      'Jumissa idean kanssa? Kysy Mestarilta mitä se ehdottaisi.',
      '"Mitä tähän vielä kannattaisi lisätä?" — Mestari miettii kanssasi.',
      'Jos et tiedä mitä seuraavaksi, kysy Mestarilta vinkkiä.',
      'Sinun ei tarvitse osata koodata. Kerro vain mitä haluat, niin Mestari rakentaa.',
      'Puhu Mestarille ihan omin sanoin — ei tarvitse mitään erikoiskäskyjä.',
      'Ei tarvitse tietää miten asiat tehdään — riittää että tiedät mitä haluat.',
      'Hyvät jutut syntyy kokeilemalla. Harva osuu täydelliseen heti.',
      'Voit muokata samaa juttua niin monta kertaa kuin haluat.',
      'Tämä on sinun ideasi — Mestari vain auttaa tekemään siitä todeksi.',
      'Pienetkin muutokset voivat tehdä isoa eroa. Kokeile vaan.',
      'Ei ole vääriä pyyntöjä. Jos jokin tuntuu hyvältä idealta, sano se.',
      'Mestari ei väsy — voit hioa juttua niin kauan kuin haluat.',
    ],
    errors: {
      sessionExpired: 'Sessio päättyi. Aloita uusi vibekoodaus.',
      sessionExpiredAction: 'Aloita uudelleen',
      networkError: 'Yhteys katkesi. Yritä uudelleen.',
      mestariNotResponding: 'Mestari ei juuri nyt vastaa. Yritä uudelleen.',
      startFailed: 'Vibekoodausta ei voitu aloittaa. Yritä uudelleen.',
    },
  },
  pikatesti: pikatestiFi,
  common: {
    back: 'Takaisin',
    loading: 'Ladataan...',
    retry: 'Yritä uudelleen',
  },
}
