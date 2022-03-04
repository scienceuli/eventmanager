// This is a minimal config.
// If you need the full config, get it from here:
// https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js

const colors = require('tailwindcss/colors')

module.exports = {
  purge: [
    // Templates within theme app (e.g. base.html)
    '../templates/**/*.html',
    // Templates in other apps. Uncomment the following line if it matches
    // your project structure or change it to match.
    // '../../templates/**/*.html',
  ],
  darkMode: false, // or 'media' or 'class'
  theme: {
    screens: {
      sm: '480px',
      md: '768px',
      lg: '976px',
      xl: '1440px',
    },
    colors: {
      gray: colors.coolGray,
      blue: colors.lightBlue,
      vfllred: '#ed1c24',
      red: colors.red,
      white: colors.white,
      green: colors.emerald,
      success: '#6B8E23',
      pink: colors.fuchsia,
    },
    fontFamily: {
      sans: ['Noto Sans JP', 'Roboto', 'sans-serif'],
      serif: ['Merriweather', 'serif'],
    },
    extend: {
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      borderRadius: {
        '4xl': '2rem',
      }
    },
    listStyleType: {
      disc: 'disc',
    }
  },
  variants: {
    extend: {},
  },
  plugins: [require('@tailwindcss/aspect-ratio'),],

}




