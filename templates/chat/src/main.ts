import type { ModelMessage } from 'ai'
import { chat, listModels, isCreditsError, CREDITS_NOTICE } from './grok.ts'
import { FORGE } from './forge.config.ts'
import './style.css'

const KEY_STORE = 'xai_api_key'
const $ = <T extends HTMLElement>(sel: string) => document.querySelector(sel) as T

document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
<header><h1>${FORGE.title}</h1><p class="idea">${escapeHtml(FORGE.idea)}</p></header>
<section class="keybox">
  <label>xAI API key <input id="key" type="password" autocomplete="off" placeholder="xai-..." /></label>
  <label class="inline"><input id="remember" type="checkbox" /> remember on this device</label>
  <button id="save">Use key</button>
  <select id="model"></select>
  ${FORGE.features.tool_calling ? '<label class="inline"><input id="tools" type="checkbox" checked /> tools</label>' : ''}
  ${FORGE.features.live_search ? '<label class="inline"><input id="web" type="checkbox" /> web search</label>' : ''}
  <p id="keynote" class="note"></p>
</section>
<main id="log"></main>
<form id="form"><textarea id="prompt" rows="3" placeholder="Ask Grok..."></textarea><button id="send">Send</button><button id="stop" type="button" disabled>Stop</button></form>
<footer>Composed by <a href="https://grokhack.com/forge">grokhack.com /forge</a> from indexed Grok integration parts: see <a href="${FORGE.repoUrl}/blob/main/PARTS.md">PARTS.md</a>.
Your key is sent only to <code>api.x.ai</code> from this browser; it is never sent to GitHub or any other server.</footer>`

const history: ModelMessage[] = []
let apiKey = localStorage.getItem(KEY_STORE) ?? sessionStorage.getItem(KEY_STORE) ?? ''
let ctrl: AbortController | null = null

async function applyKey() {
  const note = $('#keynote')
  const sel = $<HTMLSelectElement>('#model')
  if (!apiKey) {
    note.innerHTML = '<strong>Needs key:</strong> enter your own xAI API key (console.x.ai) to chat. Nothing is sent until you do.'
    sel.innerHTML = FORGE.indexModels.map((m) => `<option>${m}</option>`).join('')
    sel.value = FORGE.defaultModel
    $<HTMLButtonElement>('#send').disabled = true
    return
  }
  note.textContent = 'Checking key with api.x.ai ...'
  const { ids, live } = await listModels(apiKey)
  sel.innerHTML = ids.map((m) => `<option>${m}</option>`).join('')
  sel.value = ids.includes(FORGE.defaultModel) ? FORGE.defaultModel : ids[0]
  note.textContent = live ? `Key OK: ${ids.length} models available to this key.` : 'Could not list models with this key (invalid key or network). The chat will show the exact API error.'
  $<HTMLButtonElement>('#send').disabled = false
}

$('#save').addEventListener('click', () => {
  apiKey = $<HTMLInputElement>('#key').value.trim()
  localStorage.removeItem(KEY_STORE); sessionStorage.removeItem(KEY_STORE)
  if (apiKey) ($<HTMLInputElement>('#remember').checked ? localStorage : sessionStorage).setItem(KEY_STORE, apiKey)
  $<HTMLInputElement>('#key').value = ''
  void applyKey()
})

$('#stop').addEventListener('click', () => ctrl?.abort())

$('#form').addEventListener('submit', async (ev) => {
  ev.preventDefault()
  const text = $<HTMLTextAreaElement>('#prompt').value.trim()
  if (!text || !apiKey) return
  $<HTMLTextAreaElement>('#prompt').value = ''
  history.push({ role: 'user', content: text })
  bubble('user', text)
  const out = bubble('assistant', '')
  let acc = ''
  ctrl = new AbortController()
  $<HTMLButtonElement>('#send').disabled = true; $<HTMLButtonElement>('#stop').disabled = false
  try {
    for await (const e of chat({
      apiKey, model: $<HTMLSelectElement>('#model').value, messages: history, signal: ctrl.signal,
      useTools: $<HTMLInputElement>('#tools')?.checked ?? false, useWebSearch: $<HTMLInputElement>('#web')?.checked ?? false,
    })) {
      if (e.type === 'text') { acc += e.text; out.querySelector('.body')!.textContent = acc }
      else if (e.type === 'tool-call') meta(out, `tool call: ${e.name}(${JSON.stringify(e.input)})`)
      else if (e.type === 'tool-result') meta(out, `tool result: ${JSON.stringify(e.output).slice(0, 300)}`)
      else if (e.type === 'source') meta(out, `source: <a href="${e.url}" target="_blank" rel="noopener">${escapeHtml(e.title ?? e.url)}</a>`, true)
      else if (e.type === 'error') { out.classList.add('error'); meta(out, isCreditsError(e.message) ? `${CREDITS_NOTICE} (${e.message.slice(0, 160)})` : e.message) }
      else if (e.type === 'done' && e.usage) meta(out, `usage: ${JSON.stringify(e.usage)}`)
    }
    if (acc) history.push({ role: 'assistant', content: acc })
  } catch (err) {
    out.classList.add('error'); meta(out, String((err as Error).message ?? err))
  } finally {
    ctrl = null
    $<HTMLButtonElement>('#send').disabled = false; $<HTMLButtonElement>('#stop').disabled = true
  }
})

function bubble(role: string, text: string) {
  const el = document.createElement('div')
  el.className = `msg ${role}`
  el.innerHTML = `<div class="role">${role === 'user' ? 'You' : 'Grok'}</div><div class="body"></div>`
  el.querySelector('.body')!.textContent = text
  $('#log').appendChild(el); el.scrollIntoView({ block: 'end' })
  return el
}
function meta(el: HTMLElement, html: string, isHtml = false) {
  const m = document.createElement('div'); m.className = 'meta'
  if (isHtml) m.innerHTML = html; else m.textContent = html
  el.appendChild(m)
}
function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}
void applyKey()
