import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

export function stripFrontmatter(source: string): string {
  if (!source.startsWith('---')) return source
  const end = source.indexOf('\n---', 3)
  if (end === -1) return source
  return source.slice(end + 4).trimStart()
}

export function renderMarkdown(source: string): string {
  const html = md.render(source || '')
  const safe = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
  return safe.replace(/\[(\d{1,2})\]/g, (_match, index: string) => {
    return `<button type="button" class="cite-ref" data-cite="${index}">[${index}]</button>`
  })
}

export function plainText(source: string): string {
  return source.replace(/[#*_`>\-]/g, '').trim()
}
