// Local (client-side) tools Grok can call. Real implementations, no canned data.
import { tool } from 'ai'
import { z } from 'zod'

export function calculate(expression: string): number {
  if (!/^[\d\s+\-*/().%^]+$/.test(expression)) throw new Error('Only numbers and + - * / % ^ ( ) are allowed')
  // eslint-disable-next-line no-new-func
  const v = Function(`"use strict"; return (${expression.replace(/\^/g, '**')})`)() as unknown
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error('Result is not a finite number')
  return v
}

export function nowIn(timeZone: string, at: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-GB', { timeZone, dateStyle: 'full', timeStyle: 'long' }).format(at)
}

export async function githubRepo(fullName: string, token?: string, fetchImpl: typeof fetch = fetch) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(fullName)) throw new Error('Expected owner/name')
  const r = await fetchImpl(`https://api.github.com/repos/${fullName}`, {
    headers: { Accept: 'application/vnd.github+json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!r.ok) throw new Error(`GitHub API ${r.status}`)
  const j = (await r.json()) as Record<string, unknown> & { license?: { spdx_id?: string } | null }
  return {
    full_name: j.full_name, description: j.description, stars: j.stargazers_count, forks: j.forks_count,
    open_issues: j.open_issues_count, license: j.license?.spdx_id ?? null, pushed_at: j.pushed_at, url: j.html_url,
  }
}

export const localTools = {
  calculate: tool({
    description: 'Evaluate an arithmetic expression exactly. Use for any maths.',
    inputSchema: z.object({ expression: z.string().describe('e.g. (12.5*3)/4') }),
    execute: async ({ expression }) => ({ expression, result: calculate(expression) }),
  }),
  current_time: tool({
    description: 'Current date and time in an IANA time zone.',
    inputSchema: z.object({ timeZone: z.string().default('Europe/London') }),
    execute: async ({ timeZone }) => ({ timeZone, now: nowIn(timeZone) }),
  }),
  github_repo: tool({
    description: 'Live public GitHub repository stats (stars, forks, licence, last push).',
    inputSchema: z.object({ fullName: z.string().describe('owner/name') }),
    execute: async ({ fullName }) => githubRepo(fullName),
  }),
}
