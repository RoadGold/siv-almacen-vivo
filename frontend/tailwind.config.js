/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--canvas)',
        surface: 'var(--surface)',
        ink: {
          DEFAULT: 'var(--ink)',
          suave: 'var(--ink-suave)',
        },
        brand: {
          DEFAULT: 'var(--brand)',
          tenue: 'var(--brand-tenue)',
          hondo: 'var(--brand-hondo)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          tenue: 'var(--accent-tenue)',
        },
        warning: {
          DEFAULT: 'var(--warning)',
          tenue: 'var(--warning-tenue)',
        },
        danger: {
          DEFAULT: 'var(--danger)',
          tenue: 'var(--danger-tenue)',
        },
        muted: {
          DEFAULT: 'var(--muted)',
          tenue: 'var(--muted-tenue)',
        },
        linea: {
          DEFAULT: 'var(--linea)',
          fuerte: 'var(--linea-fuerte)',
        },
        'surface-tenue': 'var(--surface-tenue)',
        'canvas-tenue': 'var(--canvas-tenue)',
        'accent-fuerte': 'var(--accent-fuerte)',
        'danger-fuerte': 'var(--danger-fuerte)',
        overlay: 'var(--overlay)',
        'sobre-brand': 'var(--sobre-brand)',
        'sobre-ink': 'var(--sobre-ink)',
      },
      fontFamily: {
        sans: [
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      borderRadius: {
        tarjeta: '10px',
      },
      boxShadow: {
        panel: 'var(--sombra-panel)',
        elevado: 'var(--sombra-elevado)',
      },
      maxWidth: {
        contenido: '1440px',
      },
    },
  },
  plugins: [],
};
