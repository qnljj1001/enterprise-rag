import { expect, test, type Page } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const sampleFile = fileURLToPath(new URL('../../data/samples/policy_faq.md', import.meta.url))

async function gotoWithCaptcha(page: Page, path: string) {
  const responsePromise = page.waitForResponse((response) =>
    response.url().includes('/api/v1/auth/captcha'),
  )
  await page.goto(path)
  const response = await responsePromise
  return response.json()
}

async function login(page: Page, username: string, password: string) {
  const captcha = await gotoWithCaptcha(page, '/login')
  await page.getByTestId('login-username').fill(username)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-captcha').fill(captcha.debug_code)
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/chat/)
}

test('管理员建库上传解析、Wiki、用户注册问答与会话管理', async ({ page }) => {
  const unique = Date.now().toString(36)

  // 管理员登录
  await login(page, 'admin', 'admin123456')

  // 创建知识库
  await page.getByRole('link', { name: '知识库管理' }).click()
  await expect(page.getByTestId('kb-create-open')).toBeVisible()
  await page.getByTestId('kb-create-open').click()
  await page.getByTestId('kb-create-name').fill(`E2E 政策库 ${unique}`)
  await page.getByTestId('kb-create-submit').click()
  await expect(page).toHaveURL(/\/admin\/knowledge\/kb_/)

  // 上传 Markdown 并等待解析完成
  await page.getByTestId('doc-upload-open').click()
  await page.getByTestId('doc-upload-input').setInputFiles(sampleFile)
  await page.getByTestId('doc-upload-submit').click()
  await expect(page.getByTestId('doc-row').first()).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('已就绪').first()).toBeVisible({ timeout: 120_000 })

  // 预览文档块、编辑
  await page.getByTestId('doc-row').first().click()
  await expect(page).toHaveURL(/\/admin\/documents\/doc_/)
  await expect(page.getByTestId('chunk-card').first()).toBeVisible()
  await page.getByTestId('chunk-edit').first().click()
  await page
    .getByTestId('chunk-edit-content')
    .fill('这是 E2E 编辑后的内容：西部计划服务期一般为 1 至 3 年。')
  await page.getByTestId('chunk-edit-save').click()
  await expect(page.getByText('这是 E2E 编辑后的内容')).toBeVisible()

  // Wiki 只读视图
  await page.getByRole('button', { name: 'Wiki 视图' }).click()
  await expect(page).toHaveURL(/\/wiki/)
  await expect(page.getByTestId('wiki-content')).toBeVisible()
  await expect(page.getByTestId('wiki-content')).toContainText('西部计划')

  // 退出并注册普通用户
  await page.evaluate(() => localStorage.clear())
  const captcha = await gotoWithCaptcha(page, '/register')
  const username = `e2e_${unique}`
  await page.getByTestId('register-username').fill(username)
  await page.getByTestId('register-password').fill('user123456')
  await page.getByTestId('register-confirm').fill('user123456')
  await page.getByTestId('register-captcha').fill(captcha.debug_code)
  await page.getByTestId('register-submit').click()
  await expect(page).toHaveURL(/\/chat/)

  // 提问并等待流式回答与引用
  await page.getByTestId('chat-composer').fill('西部计划服务期一般是几年？')
  await page.getByTestId('chat-send').click()
  await expect(page.getByTestId('chat-message')).toHaveCount(2, { timeout: 60_000 })
  await expect(page.getByTestId('chat-citation').first()).toBeVisible({ timeout: 60_000 })
  await expect(page.getByTestId('chat-message').last()).toContainText('根据现有知识库')

  // 会话重命名
  await page.getByTestId('chat-rename').click()
  const prompt = page.getByRole('dialog')
  await expect(prompt).toBeVisible()
  await prompt.getByRole('textbox').fill('E2E 会话')
  await prompt.getByRole('button', { name: '保存' }).click()
  await expect(page.getByRole('heading', { name: 'E2E 会话' })).toBeVisible()

  // 普通用户不能进入管理端
  await page.goto('/admin/knowledge')
  await expect(page).toHaveURL(/\/chat/)

  // 删除会话
  await page.getByTestId('chat-delete').click()
  const confirm = page.getByRole('dialog')
  await expect(confirm).toBeVisible()
  await confirm.getByRole('button', { name: '删除' }).click()
  await expect(page.getByTestId('chat-message')).toHaveCount(0)
})
