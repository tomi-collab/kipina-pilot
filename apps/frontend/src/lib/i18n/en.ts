import type { Translations } from './fi'

export const en: Translations = {
  app: {
    title: 'Kipinä',
    tagline: 'IDK is not whatever anymore',
  },
  nav: {
    home: 'Home',
    logout: 'Sign out',
  },
  language: {
    label: 'Language',
    fi: 'Suomi',
    en: 'English',
  },
  login: {
    heading: 'Welcome to Kipinä',
    description:
      'Tell us about your everyday idea or challenge. AI will help you take it forward.',
    codeLabel: 'Access code',
    codePlaceholder: 'Enter code',
    submit: 'Start',
    error: 'Access code is incorrect.',
    networkError: 'Connection failed. Please try again.',
  },
  home: {
    heading: 'What are you talking about today?',
    loadingTenants: 'Loading...',
    startButton: 'Start',
  },
  idea: {
    heading: 'Tell your idea',
    placeholder:
      'Describe what came to mind, in your own words. For example: "I would like an app that..."',
    send: 'Send',
    sending: 'AI is thinking...',
    networkError: 'Connection failed. Please try again.',
    yourTurn: 'You',
    assistantTurn: 'AI',
    finishedNotice: 'Your concept is ready!',
    showConcept: 'Show concept',
  },
  concept: {
    heading: 'Your concept',
    description: 'AI shaped your idea into the following concept:',
    generateButton: 'Generate concept',
    loading: 'Generating concept...',
    errorTitle: 'Concept generation failed',
    errorRetry: 'Try again',
    generatedHeading: 'Concept',
    nextStep: 'Build a prototype',
    backToHome: 'Back to home',
  },
  prototype: {
    heading: 'Your prototype',
    description:
      'Next, an AI-assisted working prototype will be created from this.',
    placeholder:
      'This section is under construction. In the finished pilot, you will see a working wireframe of your idea here.',
    backToHome: 'Back to home',
  },
  common: {
    back: 'Back',
    loading: 'Loading...',
    retry: 'Try again',
  },
}
