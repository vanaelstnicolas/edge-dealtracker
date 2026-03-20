/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        edge: {
          bg: '#ffffff',
          text: '#000000',
          primary: '#CCBFFF',
          success: '#D0F1E3',
          muted: '#f4f4f5',
          danger: '#b42318',
        },
      },
      fontFamily: {
        heading: ['DegularDemo-Medium', 'Helvetica', 'Arial', 'sans-serif'],
        body: ['Helvetica', 'Roboto', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        card: '0 10px 24px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
}
