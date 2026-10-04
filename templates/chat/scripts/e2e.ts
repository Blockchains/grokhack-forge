// End-to-end check against the REAL xAI API using the same module the browser uses.
// With XAI_API_KEY: expects a streamed answer. Without: expects api.x.ai to reject the request (401/400/403),
// which proves the request path, headers and error handling work, and prints "needs key".
import { chat } from '../src/grok.ts'
import { FORGE } from '../src/forge.config.ts'

const key = process.env.XAI_API_KEY ?? ''
const model = process.env.XAI_MODEL ?? FORGE.defaultModel
let text = ''
let error = ''
for await (const e of chat({ apiKey: key || 'not-a-real-key', model, messages: [{ role: 'user', content: 'Reply with exactly: pong' }], useTools: false })) {
  if (e.type === 'text') text += e.text
  if (e.type === 'error') error = e.message
}
if (key) {
  if (!text) { console.error('FAIL: no text from Grok.', error); process.exit(1) }
  console.log(`PASS (live): model=${model} reply=${JSON.stringify(text.slice(0, 80))}`)
} else {
  if (!/xAI API (400|401|403)/.test(error)) { console.error('FAIL: expected an auth rejection from api.x.ai, got:', error || text); process.exit(1) }
  console.log(`PASS (needs key): api.x.ai rejected the unauthenticated request as expected -> ${error.slice(0, 120)}`)
}
