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
