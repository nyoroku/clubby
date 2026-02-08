/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './club/templates/**/*.html',
    './templates/**/*.html',
    './static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Melvins Club Brand Colors
        'melvins': {
          'red': '#a81f23', // Primary Brand Red
          'red-dark': '#a71e24', // Footer/Accents
          'red-light': '#c92e34',
          'gold': '#ee9822', // Secondary Accent
          'gold-light': '#ef9c2b',
          'green': '#245336', // Dark Green Text/Accents
          'dark': '#1b1f22', // Primary Text
          'cream': '#f8f5ec', // Backgrounds
          'white': '#ffffff',
          // Legacy mappings to prevent breaks before full refactor
          'forest': '#245336',
          'forest-light': '#2d6a45',
          'forest-dark': '#1a3c27',
          'copper': '#ee9822',
          'copper-light': '#ef9c2b',
        }
      },
      fontFamily: {
        'inter': ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'card-reveal': 'cardReveal 0.8s ease-out forwards',
        'shimmer': 'shimmer 2s linear infinite',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        cardReveal: {
          '0%': { transform: 'rotateY(180deg) scale(0.8)', opacity: '0' },
          '50%': { transform: 'rotateY(90deg) scale(1)', opacity: '0.5' },
          '100%': { transform: 'rotateY(0deg) scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(204, 139, 101, 0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(204, 139, 101, 0.6)' },
        },
      },
      backdropBlur: {
        'xs': '2px',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(1, 51, 40, 0.15)',
        'card': '0 10px 40px rgba(1, 51, 40, 0.12)',
        'card-hover': '0 20px 60px rgba(1, 51, 40, 0.2)',
        'glow': '0 0 30px rgba(204, 139, 101, 0.4)',
      },
    },
  },
  plugins: [],
}
