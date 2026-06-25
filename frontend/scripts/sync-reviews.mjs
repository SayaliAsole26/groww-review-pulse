import { copyFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const source = join(root, 'data', 'reviews_normalized.json')
const destDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'data')
const dest = join(destDir, 'reviews_normalized.json')

if (!existsSync(source)) {
  console.warn(`sync-reviews: source not found (${source}); run pulse ingest first`)
  process.exit(0)
}

mkdirSync(destDir, { recursive: true })
copyFileSync(source, dest)
console.log(`sync-reviews: copied ${source} -> ${dest}`)
