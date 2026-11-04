/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "ui-sans-serif", "system-ui"],
        display: ["Manrope", "DM Sans", "sans-serif"]
      },
      colors: {
        ink: "#202631",
        muted: "#7B8493",
        line: "#E7EAF0",
        accent: "#4969A5"
      },
      boxShadow: {
        soft: "0 10px 35px rgba(25, 35, 55, 0.06)"
      }
    }
  },
  plugins: []
};
