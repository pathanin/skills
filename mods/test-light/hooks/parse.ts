// A test runner in command position (start, or after ; & | ( ), or a --self-test flag
// or a test file run directly. `grep pytest` and `echo npm test` don't count.
const CMD = String.raw`(?:^|[;&|(]|\n)\s*(?:\w+=\S*\s+)*(?:sudo\s+)?(?:uv\s+run\s+|npx\s+|bunx\s+)?`
const RUNNER = String.raw`(?:python3?\s+-m\s+)?(?:pytest|py\.test|unittest)\b|(?:npm|yarn|pnpm|bun)\s+(?:run\s+)?test\b|vitest\b|jest\b|(?:go|cargo|swift|make|deno)\s+test\b|claude\s+plugin\s+test\b|(?:python3?|node)\s+\S*test\S*\.(?:py|m?[jt]s)\b`
const TEST = new RegExp(`${CMD}(?:${RUNNER})|\\s--self-test\\b`)

export const isTestCommand = (command: string): boolean => TEST.test(command)

const num = (text: string, re: RegExp): number => Number(text.match(re)?.[1] ?? 0)

export type Verdict = { ok: boolean; passed?: number; failed?: number }

export const verdict = (text: string, isError: boolean): Verdict => {
  const cargo = text.match(/test result: \w+\. (\d+) passed; (\d+) failed/)
  if (cargo) return counted(+cargo[1], +cargo[2], isError)

  const jest = text.match(/^Tests:.*$/m)?.[0]
  if (jest) return counted(num(jest, /(\d+) passed/), num(jest, /(\d+) failed/), isError)

  // bun / claude plugin test: " 7 pass\n 0 fail"
  const bun = text.match(/^\s*(\d+) pass\s*\n\s*(\d+) fail\s*$/m)
  if (bun) return counted(+bun[1], +bun[2], isError)

  const ran = text.match(/Ran (\d+) tests?/)
  if (ran) {
    const failed = num(text, /failures=(\d+)/) + num(text, /errors=(\d+)/)
    return counted(+ran[1] - failed, failed, isError)
  }

  if (/\d+ (passed|failed)/.test(text)) {
    return counted(num(text, /(\d+) passed/), num(text, /(\d+) failed/) + num(text, /(\d+) errors?\b/), isError)
  }

  return { ok: !isError }
}

const counted = (passed: number, failed: number, isError: boolean): Verdict => ({
  ok: !isError && failed === 0,
  passed,
  failed,
})
