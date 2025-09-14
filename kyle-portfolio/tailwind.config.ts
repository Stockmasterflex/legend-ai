import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0F14',
        card: '#121822',
        accent: '#16a34a',
        danger: '#ef4444',
        text: '#D1D5DB',
      },
      boxShadow: {
        card: '0 8px 24px rgba(0,0,0,0.25)'
      }
    },
  },
  plugins: [],
}

export default config

