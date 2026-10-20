export interface SSEFrame {
  event: string
  data: string
}

function processLines(
  buffer: string,
  final: boolean,
  state: { event: string; dataLines: string[] },
  onFrame: (frame: SSEFrame) => void,
): string {
  let remaining = buffer
  while (true) {
    const match = remaining.match(/\r\n|\r|\n/)
    if (!match || match.index === undefined) break
    if (!final && match[0] === '\r' && match.index === remaining.length - 1) break
    const index = match.index
    const separator = match[0]
    const line = remaining.slice(0, index)
    remaining = remaining.slice(index + separator.length)

    if (line === '') {
      if (state.dataLines.length > 0) {
        onFrame({ event: state.event || 'message', data: state.dataLines.join('\n') })
      }
      state.event = ''
      state.dataLines = []
      continue
    }
    if (line.startsWith(':')) continue
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') state.event = value
    else if (field === 'data') state.dataLines.push(value)
  }
  if (final && remaining.length > 0) {
    const colon = remaining.indexOf(':')
    const field = colon === -1 ? remaining : remaining.slice(0, colon)
    let value = colon === -1 ? '' : remaining.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') state.event = value
    else if (field === 'data') state.dataLines.push(value)
    remaining = ''
  }
  return remaining
}

export async function readSSEStream(
  stream: ReadableStream<Uint8Array>,
  onFrame: (frame: SSEFrame) => void,
): Promise<void> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  const state = { event: '', dataLines: [] as string[] }
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) {
        buffer += decoder.decode()
        processLines(buffer, true, state, onFrame)
        break
      }
      buffer += decoder.decode(value, { stream: true })
      buffer = processLines(buffer, false, state, onFrame)
    }
    if (state.dataLines.length > 0) {
      onFrame({ event: state.event || 'message', data: state.dataLines.join('\n') })
    }
  } finally {
    reader.releaseLock()
  }
}
