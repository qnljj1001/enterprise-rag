import { describe, expect, it } from 'vitest'

import { stripFrontmatter } from './markdown'

describe('stripFrontmatter', () => {
  it('removes YAML frontmatter', () => {
    const source = '---\ntitle: "测试"\nchunk_count: "2"\n---\n\n# 正文\n\n内容'
    expect(stripFrontmatter(source).startsWith('# 正文')).toBe(true)
  })

  it('keeps normal markdown', () => {
    expect(stripFrontmatter('# 标题')).toBe('# 标题')
  })
})
