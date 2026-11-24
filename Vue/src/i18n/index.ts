/**
 * Translations. The interface ships in Kazakh, Russian and English (SRS section 7).
 * To add a text: put the same key into all three files in ./locales and use it in a template as {{ $t('…') }}.
 * `npm run i18n:check` reports keys that are missing in one of the languages.
 */
import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import kk from './locales/kk.json'
import ru from './locales/ru.json'

export const LOCALES = [
  { code: 'kk', label: 'Қаз' },
  { code: 'ru', label: 'Рус' },
  { code: 'en', label: 'Eng' },
] as const
export type LocaleCode = (typeof LOCALES)[number]['code']
const STORAGE_KEY = 'biletflow_locale'

function initialLocale(): LocaleCode {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'kk' || saved === 'ru' || saved === 'en') return saved
  } catch {
    /* ignore */
  }
  const browser = navigator.language.slice(0, 2)
  return browser === 'kk' || browser === 'en' ? browser : 'ru'
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: 'en',
  messages: { en, ru, kk },
  // Russian plural forms: 1 билет / 2 билета / 5 билетов
  pluralRules: {
    ru: (n: number, choices: number) => {
      if (choices < 3) return n === 1 ? 0 : 1
      const mod10 = n % 10
      const mod100 = n % 100
      if (mod10 === 1 && mod100 !== 11) return 0
      if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 1
      return 2
    },
  },
})

export function setLocale(code: LocaleCode): void {
  i18n.global.locale.value = code
  document.documentElement.lang = code
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    /* ignore */
  }
}
document.documentElement.lang = i18n.global.locale.value
