import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'

import { chromium } from 'playwright'

const here = dirname(fileURLToPath(import.meta.url))
const projectRoot = resolve(here, '../..')
const html = resolve(projectRoot, 'docs/diagrams/flow.html')
const outDir = resolve(projectRoot, 'docs/diagrams')
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({
  viewport: { width: 1800, height: 1000 },
  deviceScaleFactor: 2,
})
await page.goto(pathToFileURL(html).href, { waitUntil: 'load' })
await page.waitForTimeout(500)
await page.screenshot({
  path: resolve(outDir, 'enterprise-rag-flow.png'),
  fullPage: true,
})
await browser.close()
console.log('flow diagram saved')
