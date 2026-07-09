import type { Config } from 'tailwindcss'
import defaultTheme from 'tailwindcss/defaultTheme'

const config: Config = {
  content: [
    './index.html',
    './app.html',
    './docs.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', ...defaultTheme.fontFamily.sans],
        mono: ['JetBrains Mono', ...defaultTheme.fontFamily.mono],
      },
      colors: {
        background: '#030303',
        foreground: '#ffffff',
        surface: '#0a0a0a',
        'surface-accent': '#111111',
        accent: '#00ff88',
        'accent-dim': 'rgba(0, 255, 136, 0.06)',
        'accent-glow': 'rgba(0, 255, 136, 0.15)',
        secondary: '#a78bfa',
        'secondary-glow': 'rgba(167, 139, 250, 0.15)',
        warn: '#f59e0b',
        'text-primary': '#ffffff',
        'text-secondary': '#a1a1aa',
        'text-muted': '#52525b',
      },
      backgroundColor: {
        DEFAULT: '#030303',
      },
      textColor: {
        DEFAULT: '#ffffff',
      },
      borderColor: {
        DEFAULT: 'rgba(255, 255, 255, 0.08)',
      },
      keyframes: {
        'fade-in-up': {
          '0%': {
            opacity: '0',
            transform: 'translateY(20px)',
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        'pulse-glow': {
          '0%, 100%': {
            opacity: '1',
          },
          '50%': {
            opacity: '0.8',
          },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
export default config
