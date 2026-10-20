import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from 'playwright'

const here = dirname(fileURLToPath(import.meta.url))
const outDir = resolve(here, '../../docs/screenshots')
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 940 } })

async function gotoWithCaptcha(path) {
  const responsePromise = page.waitForResponse((response) =>
    response.url().includes('/api/v1/auth/captcha'),
  )
  await page.goto(`http://127.0.0.1:5174${path}`)
  return responsePromise
}

const loginCaptcha = await gotoWithCaptcha('/login')
await page.waitForTimeout(600)
await page.screenshot({ path: resolve(outDir, '01-login.png'), fullPage: true })

const captcha = await (await loginCaptcha).json()
await page.getByTestId('login-username').fill('admin')
await page.getByTestId('login-password').fill('admin123456')
await page.getByTestId('login-captcha').fill(captcha.debug_code)
await page.getByTestId('login-submit').click()
await page.waitForURL('**/chat')
await page.waitForTimeout(1200)
await page.getByTestId('chat-composer').fill('西部计划服务期一般是几年？')
await page.getByTestId('chat-send').click()
await page.getByTestId('chat-citation').first().waitFor({ timeout: 60_000 })
await page.waitForTimeout(800)
await page.screenshot({ path: resolve(outDir, '02-chat.png'), fullPage: true })

await page.goto('http://127.0.0.1:5174/admin/knowledge')
await page.waitForTimeout(900)
await page.screenshot({ path: resolve(outDir, '03-knowledge-list.png'), fullPage: true })

const firstCard = page.getByTestId('kb-card').first()
if (await firstCard.count()) {
  await firstCard.click()
  await page.waitForTimeout(1200)
  await page.screenshot({ path: resolve(outDir, '04-knowledge-detail.png'), fullPage: true })
  const wikiButton = page.getByRole('button', { name: 'Wiki 视图' })
  if (await wikiButton.count()) {
    await wikiButton.click()
    await page.waitForTimeout(900)
    await page.screenshot({ path: resolve(outDir, '05-wiki.png'), fullPage: true })
  }
}

await page.evaluate(() => localStorage.clear())
const registerCaptcha = await gotoWithCaptcha('/register')
await page.waitForTimeout(600)
await page.screenshot({ path: resolve(outDir, '06-register.png'), fullPage: true })
await (await registerCaptcha).json()

await browser.close()
console.log(`screenshots saved to ${outDir}`)
