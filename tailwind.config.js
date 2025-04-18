/** @type {import('tailwindcss').Config} */

const colors = require('tailwindcss/colors')

export default {
  content: [
    "./eventmanager/**/*.{js,jsx,ts,tsx}",
    "./**/templates/**/*.html",
  ],
  theme: {
    screens: {
      sm: '480px',
      md: '768px',
      lg: '976px',
      xl: '1440px',
    },
    colors: {
      gray: colors.gray,
      blue: colors.sky,
      vfllred: '#ed1c24',
      red: colors.red,
      white: colors.white,
      green: colors.emerald,
      success: '#6B8E23',
      pink: colors.fuchsia,
      black: colors.black,
    },
    fontFamily: {
      sans: ['Noto Sans', 'Roboto', 'sans-serif'],
      serif: ['Merriweather', 'serif'],
    },
    extend: {
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      width: {
        '128': '32rem',
      },
      height: {
        '128': '32rem',
      }
    },
    listStyleType: {
      disc: 'disc',
    }
  },
  variants: {
    extend: {},
  },
  plugins: [
    /**
     * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
     * for forms. If you don't like it or have own styling for forms,
     * comment the line below to disable '@tailwindcss/forms'.
     */
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/line-clamp'),
    require('@tailwindcss/aspect-ratio'),
  ],
}