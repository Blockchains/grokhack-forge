// Grok integration layer: Vercel AI SDK + @ai-sdk/xai (indexed from Blockchains/ai packages/xai).
import { createXai } from '@ai-sdk/xai'
import { stepCountIs, streamText, type ModelMessage } from 'ai'
import { FORGE } from './forge.config.ts'
import { localTools } from './tools.ts'

export const XAI_BASE_URL = 'https://api.x.ai/v1'

export type StreamEvent =
  | { type: 'text'; text: string }
  | { type: 'tool-call'; name: string; input: unknown }
  | { type: 'tool-result'; name: string; output: unknown }
  | { type: 'source'; url: string; title?: string }
  | { type: 'error'; message: string }
  | { type: 'done'; usage?: unknown }

/** Live model list for this key (GET /v1/language-models). Falls back to the models found in the index. */
export async function listModels(apiKey: string, fetchImpl: typeof fetch = fetch): Promise<{ ids: string[]; live: boolean }> {
  try {
    const r = await fetchImpl(`${XAI_BASE_URL}/language-models`, { headers: { Authorization: `Bearer ${apiKey}` } })
    if (!r.ok) throw new Error(String(r.status))
    const j = (await r.json()) as { models?: { id: string }[] }
    const ids = (j.models ?? []).map((m) => m.id).filter(Boolean)
    if (ids.length) return { ids, live: true }
  } catch {
    /* fall through to index models */
  }
  return { ids: [...FORGE.indexModels], live: false }
}

export async function* chat(opts: {
  apiKey: string
  model: string
  messages: ModelMessage[]
  useTools?: boolean
  useWebSearch?: boolean
  signal?: AbortSignal
}): AsyncGenerator<StreamEvent> {
  const xai = createXai({ apiKey: opts.apiKey, baseURL: XAI_BASE_URL })
  const tools = {
    ...(opts.useTools && FORGE.features.tool_calling ? localTools : {}),
    ...(opts.useWebSearch && FORGE.features.live_search ? { web_search: xai.tools.webSearch() } : {}),
  }
  let failed: string | null = null
  const result = streamText({
    model: xai.responses(opts.model),
    system: FORGE.systemPrompt,
    messages: opts.messages,
    tools,
    stopWhen: stepCountIs(5),
    abortSignal: opts.signal,
    onError: ({ error }) => {
      failed = describeError(error)
    },
  })
  for await (const part of result.fullStream) {
    switch (part.type) {
      case 'text-delta':
        yield { type: 'text', text: part.text }
        break
      case 'tool-call':
        yield { type: 'tool-call', name: part.toolName, input: part.input }
        break
      case 'tool-result':
        yield { type: 'tool-result', name: part.toolName, output: part.output }
        break
      case 'source':
        if (part.sourceType === 'url') yield { type: 'source', url: part.url, title: part.title }
        break
      case 'error':
        failed = describeError(part.error)
        break
    }
  }
  if (failed) {
    yield { type: 'error', message: failed }
    return
  }
  yield { type: 'done', usage: await result.totalUsage }
}

export function describeError(e: unknown): string {
  const any = e as { statusCode?: number; responseBody?: string; message?: string }
  if (any?.statusCode) {
    let detail = any.responseBody ?? ''
    try {
      const j = JSON.parse(detail) as { error?: string | { message?: string }; code?: string }
      detail = typeof j.error === 'string' ? j.error : j.error?.message ?? j.code ?? detail
    } catch {
      /* keep raw */
    }
    return `xAI API ${any.statusCode}: ${String(detail).slice(0, 300)}`
  }
  return String(any?.message ?? e).slice(0, 300)
}
