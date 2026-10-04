import { test } from 'node:test'
import assert from 'node:assert/strict'
import { calculate, githubRepo, nowIn } from '../src/tools.ts'

test('calculate evaluates arithmetic exactly', () => {
  assert.equal(calculate('(12.5*3)/4'), 9.375)
  assert.equal(calculate('2^10'), 1024)
  assert.throws(() => calculate('process.exit()'))
})

test('nowIn formats a real date in a time zone', () => {
  const s = nowIn('Europe/London', new Date('2026-10-03T18:00:00Z'))
  assert.match(s, /3 October 2026/)
  assert.match(s, /19:00:00/)
})

test('githubRepo returns live stats from the GitHub API', async () => {
  const r = await githubRepo('xai-org/xai-sdk-python', process.env.GITHUB_TOKEN)
  assert.equal(r.full_name, 'xai-org/xai-sdk-python')
  assert.ok(typeof r.stars === 'number' && r.stars > 0)
})

test('credits-exhausted 403 from api.x.ai is recognised (shown as "xAI credits needed")', async () => {
  const { isCreditsError } = await import('../src/grok.ts')
  assert.ok(isCreditsError('xAI API 403: Your team has either used all available credits or reached its monthly spending limit.'))
  assert.ok(!isCreditsError('xAI API 400: Incorrect API key provided.'))
})
