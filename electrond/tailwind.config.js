/** @type {import('tailwindcss').Config} */
// tailwind config for da editor - pink vibes all day

module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // main pink theme - we dont play with these
        'da-dark': '#0d0d14',
        'da-darker': '#080810',
        'da-medium': '#14141f',
        'da-light': '#1a1a2e',
        'da-pink': '#e94560',
        'da-pink-hover': '#ff6b8a',
        'da-pink-glow': '#ff4d6d',
        'da-success': '#4ecca3',
        'da-warning': '#feca57',
        'da-error': '#ff6b6b',
        'da-text': '#ffffff',
        'da-text-dim': '#8a8a9e',
        'da-text-muted': '#5a5a6e'
      },
      fontFamily: {
        'main': ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'confetti': 'confetti 1s ease-out forwards'
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px #e94560, 0 0 10px #e94560' },
          '100%': { boxShadow: '0 0 20px #e94560, 0 0 30px #e94560' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        confetti: {
          '0%': { transform: 'scale(0.5)', opacity: '1' },
          '50%': { transform: 'scale(1.2)', opacity: '1' },
          '100%': { transform: 'scale(1)', opacity: '0' }
        }
      },
      boxShadow: {
        'pink': '0 0 20px rgba(233, 69, 96, 0.3)',
        'pink-lg': '0 0 40px rgba(233, 69, 96, 0.4)'
      }
    },
  },
  plugins: [],
}
