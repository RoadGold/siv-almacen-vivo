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
        panel: '0 1px 2px rgba(25, 42, 49, 0.05)',
        elevado: '0 8px 24px rgba(25, 42, 49, 0.12)',
      },
      maxWidth: {
        contenido: '1440px',
      },
    },
  },
  plugins: [],
};
