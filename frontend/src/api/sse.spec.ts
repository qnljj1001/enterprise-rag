import { describe, expect, it } from 'vitest'

import { readSSEStream, type SSEFrame } from './sse'

function streamFrom(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

describe('readSSEStream', () => {
  it('parses multiple frames and multiline data', async () => {
    const frames: SSEFrame[] = []
    await readSSEStream(
      streamFrom([
        'event: meta\ndata: {"a":1}\n\n',
        'event: delta\ndata: 第一行\ndata: 第二行\n\n: ping\n\n',
        'event: done\ndata: {"ok":true}\n\n',
      ]),
      (frame) => frames.push(frame),
    )
    expect(frames).toHaveLength(3)
    expect(frames[0]).toEqual({ event: 'meta', data: '{"a":1}' })
    expect(frames[1]).toEqual({ event: 'delta', data: '第一行\n第二行' })
    expect(frames[2]).toEqual({ event: 'done', data: '{"ok":true}' })
  })

  it('handles a frame split across chunks', async () => {
    const frames: SSEFrame[] = []
    await readSSEStream(streamFrom(['event: del', 'ta\ndata: 你', '好\n\n']), (frame) =>
      frames.push(frame),
    )
    expect(frames).toEqual([{ event: 'delta', data: '你好' }])
  })
})
