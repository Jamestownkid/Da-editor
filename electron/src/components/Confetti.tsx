/**
 * Da Editor - Confetti Component
 * ================================
 * celebration animation when job starts
 * we making this app feel alive
 * 
 * nothing crazy just some moving colors
 */

import React, { useEffect, useState } from 'react'

interface Particle {
  id: number
  x: number
  y: number
  color: string
  rotation: number
  scale: number
  velocity: { x: number; y: number }
}

export default function Confetti() {
  const [particles, setParticles] = useState<Particle[]>([])

  // 1a. create particles on mount
  useEffect(() => {
    const colors = ['#e94560', '#ff6b8a', '#4ecca3', '#feca57', '#ffffff']
    const newParticles: Particle[] = []

    for (let i = 0; i < 50; i++) {
      newParticles.push({
        id: i,
        x: Math.random() * window.innerWidth,
        y: window.innerHeight / 2 - 100,
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * 360,
        scale: 0.5 + Math.random() * 0.5,
        velocity: {
          x: (Math.random() - 0.5) * 20,
          y: -10 - Math.random() * 10
        }
      })
    }

    setParticles(newParticles)

    // animate particles
    let frame: number
    const animate = () => {
      setParticles(prev => prev.map(p => ({
        ...p,
        x: p.x + p.velocity.x,
        y: p.y + p.velocity.y,
        rotation: p.rotation + 5,
        velocity: {
          ...p.velocity,
          y: p.velocity.y + 0.5 // gravity
        }
      })).filter(p => p.y < window.innerHeight + 100))
      
      frame = requestAnimationFrame(animate)
    }

    frame = requestAnimationFrame(animate)

    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
      {/* particles */}
      {particles.map(p => (
        <div
          key={p.id}
          className="absolute w-3 h-3 rounded-sm"
          style={{
            left: p.x,
            top: p.y,
            backgroundColor: p.color,
            transform: `rotate(${p.rotation}deg) scale(${p.scale})`,
            opacity: Math.max(0, 1 - (p.y / window.innerHeight))
          }}
        />
      ))}

      {/* center burst text */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-4xl font-bold text-da-pink animate-pulse drop-shadow-lg">
          JOB STARTED!
        </div>
      </div>
    </div>
  )
}

