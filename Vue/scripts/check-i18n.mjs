/**
 * Translation check:  npm run i18n:check
 *
 * 1. every key used in the source code exists in en.json
 * 2. kk.json and ru.json have exactly the same keys as en.json
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const root = new URL('..', import.meta.url).pathname
const load = (name) => JSON.parse(readFileSync(join(root, 'src/i18n/locales', `${name}.json`), 'utf8'))

function flatten(object, prefix = '') {
  return Object.entries(object).flatMap(([key, value]) =>
    typeof value === 'object' && value !== null ? flatten(value, `${prefix}${key}.`) : [`${prefix}${key}`])
}
function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : /\.(vue|ts)$/.test(name) ? [path] : []
  })
}

const en = new Set(flatten(load('en')))
let problems = 0

// Keys written literally in the code: t('a.b'), $t("a.b"), te('a.b')
const used = new Set()
const dynamic = new Set()
for (const file of files(join(root, 'src'))) {
  const text = readFileSync(file, 'utf8')
  for (const match of text.matchAll(/\bt[e]?\(\s*['"]([\w.]+)['"]/g)) used.add(match[1])
  for (const match of text.matchAll(/\$t\(\s*['"]([\w.]+)['"]/g)) used.add(match[1])
  // keys built from a variable, e.g. $t(`status.${value}`): remember the fixed beginning
  for (const match of text.matchAll(/\bt\(\s*`([\w.]+)\.\$\{/g)) dynamic.add(match[1])
}
for (const key of [...used].sort()) {
  if (!en.has(key)) {
    console.log(`missing in en.json: ${key}`)
    problems++
  }
}
for (const prefix of [...dynamic].sort()) {
  if (![...en].some((key) => key.startsWith(`${prefix}.`))) {
    console.log(`no keys under "${prefix}." in en.json (used with a variable)`)
    problems++
  }
}

for (const locale of ['ru', 'kk']) {
  const keys = new Set(flatten(load(locale)))
  for (const key of en) if (!keys.has(key)) (console.log(`missing in ${locale}.json: ${key}`), problems++)
  for (const key of keys) if (!en.has(key)) (console.log(`extra in ${locale}.json: ${key}`), problems++)
}

console.log(problems ? `\n${problems} problem(s)` : `OK: ${en.size} keys in 3 languages, ${used.size} used directly in code`)
process.exit(problems ? 1 : 0)
