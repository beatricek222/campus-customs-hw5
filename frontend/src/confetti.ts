/** A burst of navy, white, sky and gold bubbles from a point. Respects reduced-motion. */
export function fireConfetti(x = window.innerWidth / 2, y = window.innerHeight / 3, count = 90) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const canvas = document.createElement('canvas')
  canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:9999'
  const dpr = window.devicePixelRatio || 1
  canvas.width = window.innerWidth * dpr
  canvas.height = window.innerHeight * dpr
  document.body.appendChild(canvas)
  const ctx = canvas.getContext('2d')!
  ctx.scale(dpr, dpr)
  const colors = ['#ffffff', '#cfe3ff', '#62d0ff', '#f4c95d', '#2b5fb8', '#00356B']
  const parts = Array.from({ length: count }, () => {
    const a = Math.random() * Math.PI * 2
    const s = 4 + Math.random() * 9
    return { x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 6, r: 3 + Math.random() * 6, c: colors[(Math.random() * colors.length) | 0], ring: Math.random() < 0.4, life: 1 }
  })
  const tick = () => {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
    let alive = false
    for (const p of parts) {
      p.vy += 0.28; p.vx *= 0.985; p.x += p.vx; p.y += p.vy; p.life -= 0.011
      if (p.life <= 0) continue
      alive = true
      ctx.globalAlpha = Math.max(0, p.life)
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      if (p.ring) { ctx.strokeStyle = p.c; ctx.lineWidth = 2; ctx.stroke() } else { ctx.fillStyle = p.c; ctx.fill() }
    }
    if (alive) requestAnimationFrame(tick); else canvas.remove()
  }
  requestAnimationFrame(tick)
}
