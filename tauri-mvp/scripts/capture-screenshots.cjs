const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const baseUrl = process.env.WRITER_SCREENSHOT_URL || 'http://127.0.0.1:1420'
const outDir = path.resolve(__dirname, '..', 'docs', 'assets', 'screenshots')

async function waitForApp(page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(1200)
}

async function shot(page, route, filename, options = {}) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' })
  await waitForApp(page)
  if (options.before) {
    await options.before(page)
    await page.waitForTimeout(800)
  }
  await page.screenshot({
    path: path.join(outDir, filename),
    fullPage: false,
  })
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true })
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  }).catch(() => chromium.launch({ headless: true }))
  const page = await browser.newPage({
    viewport: { width: 1440, height: 920 },
    deviceScaleFactor: 1,
  })

  await shot(page, '/articles', 'article-writing.png')
  await shot(page, '/articles', 'focus-mode.png', {
    before: async (page) => {
      await page.keyboard.press('F11')
    },
  })
  await shot(page, '/collections', 'collections.png')
  await shot(page, '/library', 'reference-library.png')
  await shot(page, '/ai?tab=chat', 'ai-workspace.png')
  await shot(page, '/settings', 'settings.png')

  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
