/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SF Mono', 'Menlo', 'Cascadia Mono', 'monospace'],
      },
      colors: {
        ground:  '#F4F6FB',
        surface: '#FFFFFF',
        border:  '#E5E8F2',
        nav:     '#1A2035',
        accent:  '#5B6BF8',
        warm:    '#F0A500',
        danger:  '#EF4444',
        success: '#10B981',
        ink: {
          900: '#111827',
          700: '#374151',
          500: '#6B7280',
          300: '#9CA3AF',
        },
      },
      boxShadow: {
        card:           '0 1px 3px rgba(17,24,39,0.06), 0 4px 16px rgba(17,24,39,0.04)',
        'card-urgent':  'inset 4px 0 0 #EF4444, 0 1px 3px rgba(17,24,39,0.06), 0 4px 16px rgba(17,24,39,0.04)',
        'card-warm':    'inset 4px 0 0 #F0A500, 0 1px 3px rgba(17,24,39,0.06), 0 4px 16px rgba(17,24,39,0.04)',
        'card-accent':  'inset 4px 0 0 #5B6BF8, 0 1px 3px rgba(17,24,39,0.06), 0 4px 16px rgba(17,24,39,0.04)',
        'card-muted':   'inset 4px 0 0 #E5E8F2, 0 1px 3px rgba(17,24,39,0.06), 0 4px 16px rgba(17,24,39,0.04)',
      },
      animation: {
        'card-enter': 'cardEnter 0.35s ease-out both',
        'pulse-dot':  'dotPulse 1.4s ease-in-out infinite',
        'shimmer':    'shimmer 1.4s ease-in-out infinite',
      },
      keyframes: {
        cardEnter: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)'   },
        },
        dotPulse: {
          '0%, 80%, 100%': { transform: 'scale(0.6)', opacity: '0.4' },
          '40%':           { transform: 'scale(1)',   opacity: '1'   },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-600px 0' },
          '100%': { backgroundPosition:  '600px 0' },
        },
      },
      letterSpacing: {
        tighter: '-0.025em',
        widest:  '0.09em',
      },
    },
  },
  plugins: [],
}
