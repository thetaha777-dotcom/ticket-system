# BiletFlow web app

The web interface for attendees, organizers and platform admins. Vue 3 with `<script setup>` and
TypeScript, built with Vite; Pinia for state, Vue Router for pages, vue-i18n for the three languages
(Kazakh, Russian, English) and Tailwind CSS 4 for styling.

## Run

```bash
npm install
npm run dev          # http://localhost:5173, reloads as you edit
```

The API must be running (see the main [README](../README.md)). Its address comes from
`VITE_API_URL`; copy `.env.example` to `.env` to change it from the default `http://localhost:8000`.

| Command | What it does |
|---|---|
| `npm run dev` | Development server with hot reload |
| `npm run type-check` | Checks every component against the TypeScript types (`vue-tsc`) |
| `npm run build` | Type check, then production build into `dist/` |
| `npm run preview` | Serves the production build locally |
| `npm run i18n:check` | Fails if a translation key is missing in one language or used in code but not defined |

## Where things are

```
src/
  main.ts              starts the app: Pinia, router, i18n, fonts, styles
  App.vue              page frame: top bar, language switch, footer, toasts
  styles.css           design tokens (colours, fonts) and shared classes: .btn, .input, .card, .table, .badge, .ticket
  types.ts             TypeScript shapes of the API's JSON (keep in step with the backend schemas)
  router/index.ts      every page address and who may open it
  stores/
    auth.ts            the signed-in user and token
    toast.ts           short confirmation messages
  lib/
    api.ts             the only place that calls fetch(): adds the token, turns error answers into ApiError
    format.ts          money, dates in the event's time zone, translated error text
    managed.ts         shares the loaded event between the tabs of the organizer's event pages
  i18n/locales/        en.json, ru.json, kk.json
  components/          reusable pieces: SeatMap, TicketPass, QrCode, BarChart, ModalDialog, ...
  views/               one file per page
    auth/              sign in, register, verify email, reset password
    organizer/         dashboard, event form, and the tabs of one event (Manage*.vue)
    admin/             platform administration
```

## How a page talks to the API

```ts
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import type { EventDetail } from '@/types'

const event = ref<EventDetail | null>(null)
const problem = ref('')

try {
  event.value = await api.get<EventDetail>(`/events/${slug}`)
} catch (error) {
  problem.value = errorText(error)      // translated message for the API's error code
}
```

`api.get / post / put / patch / delete` prefix the path with `/api/v1`, send the login token and
parse JSON. `api.download` and `api.blobUrl` fetch files (PDF tickets, QR images) with the token.
When the API answers 401 the user is signed out and sent to the sign-in page.

**Errors.** The API answers `{ "detail": "...", "code": "sold_out" }`. `errorText` looks up
`errors.sold_out` in the current language and falls back to a generic message. When you add an error
code on the backend, add `errors.<code>` to all three locale files.

## Adding a page

1. Create `src/views/MyView.vue`.
2. Add a route in `src/router/index.ts`. Use `meta: { auth: true }` for signed-in users,
   `meta: { organizer: true }` or `meta: { admin: true }` for those roles.
3. Put every visible text into the locale files and use `$t('section.key')` in the template.
   Run `npm run i18n:check`.
4. If the page uses a new API response, describe it in `src/types.ts`.

## Translations

All text lives in `src/i18n/locales/{en,ru,kk}.json`; never write visible text directly in a
component. Plurals use vue-i18n's pipe syntax: `"{n} ticket | {n} tickets"`. Dates and money are
formatted in `lib/format.ts` (Kazakh month and weekday names are written out there because browsers
do not ship them reliably). The language chosen in the top bar is remembered in the
browser; the *Preferred language* on the Account page is stored with the account.

The Kazakh translation was written without a native-speaker review - please proofread it.

## Design notes

- **Tokens** are CSS variables in `styles.css` under `@theme`: ink (text), sky (primary actions),
  sun (the buy / pay action), mist (page background) and status colours. Change a colour there, not
  in components.
- **Fonts**: Oswald for headings and prices, Golos Text for everything else. Both contain the Kazakh
  letters and the tenge sign and are bundled with the app (no request to a font service).
- **The ticket shape** (`.ticket`, `.pass`) is drawn with CSS masks; event cards and ticket passes use it.
- **Accessibility**: every control has a label, focus is always visible, colour is never the only
  signal (seat states and statuses also carry a symbol or text), dialogs trap focus, and motion is
  reduced when the system asks for it. Keep it that way when adding screens.
- **Charts** (`BarChart.vue`) are plain SVG with a tooltip and a "show as table" switch - no chart library.

## Production build

`Dockerfile` builds the app and serves it with nginx; `nginx.conf` sends every unknown path to
`index.html` so that links such as `/e/some-event` work. The API address is compiled into the build:

```bash
docker build --build-arg VITE_API_URL=https://api.example.com -t biletflow-web .
```
