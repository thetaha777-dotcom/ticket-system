/** Formatting helpers: money in KZT, dates in the event's own time zone, translated API errors. */
import { i18n } from '@/i18n'

import { ApiError } from './api'

const LOCALE_TAGS: Record<string, string> = { kk: 'kk-KZ', ru: 'ru-RU', en: 'en-GB' }
const tag = (): string => LOCALE_TAGS[i18n.global.locale.value] ?? 'ru-RU'

/** 12500 -> "12 500 ₸" */
export function money(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '—'
  return `${new Intl.NumberFormat('ru-RU').format(amount)} ₸`
}

// Kazakh month and weekday names are written out here because desktop browsers often ship
// without Kazakh date data and would print "M12" instead of "желтоқсан".
const KK_MONTHS = ['қаңтар', 'ақпан', 'наурыз', 'сәуір', 'мамыр', 'маусым', 'шілде', 'тамыз', 'қыркүйек', 'қазан', 'қараша', 'желтоқсан']
const KK_MONTHS_SHORT = ['қаң', 'ақп', 'нау', 'сәу', 'мам', 'мау', 'шіл', 'там', 'қыр', 'қаз', 'қар', 'жел']
const KK_WEEKDAYS: Record<string, string> = { Mon: 'дүйсенбі', Tue: 'сейсенбі', Wed: 'сәрсенбі', Thu: 'бейсенбі', Fri: 'жұма', Sat: 'сенбі', Sun: 'жексенбі' }

interface Parts { year: string; month: number; day: string; hour: string; minute: string; weekday: string }

/** The pieces of a date in the given time zone (the browser's zone when none is given). */
function parts(iso: string, timeZone?: string): Parts {
  const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'numeric', day: '2-digit', hour: '2-digit', minute: '2-digit', weekday: 'short', hourCycle: 'h23' }
  let list: Intl.DateTimeFormatPart[]
  try {
    list = new Intl.DateTimeFormat('en-GB', { ...options, timeZone }).formatToParts(new Date(iso))
  } catch {
    list = new Intl.DateTimeFormat('en-GB', options).formatToParts(new Date(iso))
  }
  const get = (type: string): string => list.find((part) => part.type === type)?.value ?? ''
  return { year: get('year'), month: Number(get('month')), day: get('day'), hour: get('hour'), minute: get('minute'), weekday: get('weekday') }
}

function fmt(iso: string, options: Intl.DateTimeFormatOptions, timeZone?: string): string {
  try {
    return new Intl.DateTimeFormat(tag(), { ...options, timeZone }).format(new Date(iso))
  } catch {
    return new Intl.DateTimeFormat(tag(), options).format(new Date(iso))
  }
}
const isKazakh = (): boolean => i18n.global.locale.value === 'kk'

/** "12 декабря 2026 г., 19:00" in the given zone (the event's zone for events, the browser's otherwise). */
export function dateTime(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return '—'
  if (isKazakh()) {
    const p = parts(iso, timeZone)
    return `${Number(p.day)} ${KK_MONTHS[p.month - 1]} ${p.year} ж., ${p.hour}:${p.minute}`
  }
  return fmt(iso, { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }, timeZone)
}
export function dateOnly(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return '—'
  if (isKazakh()) {
    const p = parts(iso, timeZone)
    return `${Number(p.day)} ${KK_MONTHS_SHORT[p.month - 1]}. ${p.year}`
  }
  return fmt(iso, { day: 'numeric', month: 'short', year: 'numeric' }, timeZone)
}
export function timeOnly(iso: string, timeZone?: string): string {
  const p = parts(iso, timeZone)
  return `${p.hour}:${p.minute}`
}
export const dayNumber = (iso: string, timeZone?: string): string => parts(iso, timeZone).day
export const monthShort = (iso: string, timeZone?: string): string =>
  isKazakh() ? KK_MONTHS_SHORT[parts(iso, timeZone).month - 1] : fmt(iso, { month: 'short' }, timeZone).replace('.', '')
export const weekday = (iso: string, timeZone?: string): string =>
  isKazakh() ? KK_WEEKDAYS[parts(iso, timeZone).weekday] : fmt(iso, { weekday: 'long' }, timeZone)

/** Value for <input type="datetime-local"> shown in the event's time zone. */
export function toLocalInput(iso: string | null | undefined, timeZone: string): string {
  if (!iso) return ''
  const parts = new Intl.DateTimeFormat('sv-SE', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso))
  return parts.replace(' ', 'T')
}

/** Reverse of toLocalInput: "2026-12-12T19:00" typed for `timeZone` -> ISO string in UTC. */
export function fromLocalInput(value: string, timeZone: string): string | null {
  if (!value) return null
  const asUtc = new Date(`${value}:00Z`)
  // How far the zone is from UTC at that moment (Kazakhstan: +5 h, no daylight saving time).
  const shown = new Date(toLocalInput(asUtc.toISOString(), timeZone) + ':00Z')
  return new Date(asUtc.getTime() - (shown.getTime() - asUtc.getTime())).toISOString()
}

/** Message for a failed API call: our translation of the error code when we have one, else the server text. */
export function errorText(error: unknown): string {
  const { t, te } = i18n.global
  if (error instanceof ApiError) {
    const key = `errors.${error.code}`
    return te(key) ? t(key) : error.detail
  }
  return t('errors.unknown')
}

/** Stable colour for an event category, in the spirit of coloured ticket rolls. */
const ROLL_COLOURS = ['#ffc233', '#7fd6e6', '#ff9eb5', '#9be0b0', '#c8b3ff', '#ffb27a']
export function categoryColour(category: string): string {
  let hash = 0
  for (const ch of category) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return ROLL_COLOURS[hash % ROLL_COLOURS.length]
}

/** Text of one order / quote line: "Standard × 2", or "Parterre, row 4, seat 7" for an assigned seat. */
export function lineLabel(line: { name: string; quantity: number; seat_section: string | null; seat_row: string | null; seat_number: number | null }): string {
  const { t } = i18n.global
  if (!line.seat_row) return `${line.name} × ${line.quantity}`
  const seat = `${line.seat_section}, ${t('seat.rowN', { row: line.seat_row })}, ${t('seat.seatN', { n: line.seat_number })}`
  return line.name === line.seat_section ? seat : `${line.name}: ${seat}`
}
