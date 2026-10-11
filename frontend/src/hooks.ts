import { useEffect, useRef, useState } from 'react'

/** Smoothly animates a number toward its latest value (used for the checking balance). */
export function useAnimatedNumber(target: number | null, ms = 1100): number | null {
  const [value, setValue] = useState<number | null>(target)
  const from = useRef<number | null>(target)
  useEffect(() => {
    if (target === null) return
    if (from.current === null) { from.current = target; setValue(target); return }
    const start = performance.now()
    const a = from.current
    let raf = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      const eased = 1 - Math.pow(1 - t, 3)
      const v = a + (target - a) * eased
      from.current = v
      setValue(v)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return value
}

/** Calls `fn` every `ms` while `enabled`. */
export function useInterval(fn: () => void, ms: number, enabled = true) {
  const saved = useRef(fn)
  saved.current = fn
  useEffect(() => {
    if (!enabled) return
    const id = setInterval(() => saved.current(), ms)
    return () => clearInterval(id)
  }, [ms, enabled])
}
