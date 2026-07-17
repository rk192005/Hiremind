/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hm: {
          bg: '#000000',
          violet: '#7C3AED',
          cyan: '#22D3EE',
          surface: 'rgba(12, 12, 20, 0.8)',
          'surface-border': 'rgba(124, 58, 237, 0.3)',
          text: '#FFFFFF',
          'text-muted': '#94A3B8',
          danger: '#f87171',
          warning: '#fbbf24',
          success: '#34d399',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backdropBlur: {
        'xl': '24px',
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'gradient-drift': 'gradient-drift 15s ease infinite',
        'border-glow': 'border-glow 3s ease-in-out infinite',
        'score-fill': 'score-fill 1.5s ease-out forwards',
        'fade-in-up': 'fade-in-up 0.6s ease-out forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(34, 211, 238, 0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(34, 211, 238, 0.6)' },
        },
        'gradient-drift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'border-glow': {
          '0%, 100%': { borderColor: 'rgba(34, 211, 238, 0.2)' },
          '50%': { borderColor: 'rgba(34, 211, 238, 0.5)' },
        },
        'score-fill': {
          '0%': { strokeDashoffset: '283' },
          '100%': { strokeDashoffset: 'var(--score-offset)' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
