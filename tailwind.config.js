/*
 * Gedeelde Tailwind-configuratie voor de hele EAA Hub.
 * Eén bron van waarheid voor kleuren en typografie (voorheen
 * public/static/theme.js + de Tailwind-CDN; nu een lokale build).
 *
 * Na een wijziging hier of in de gebruikte classes:
 *   npm run build:css
 *
 * Designrichting: Coinbase-look. Neutrale eigen huisstijl voor de EAA Monitor,
 * niet gekoppeld aan een ander merk.
 */
module.exports = {
  content: [
    "./public/**/*.html",
    "./public/**/*.js",
    "./tools/*.py", // HTML-templates in Python-strings (build-tools en scraper)
  ],
  theme: {
    extend: {
      colors: {
        // Primair (Coinbase-blauw). 'bright' is een lichtere tint voor
        // accenttekst op donkere achtergronden (contrast >= 4.5:1 op navy).
        brand: { DEFAULT: '#0052FF', dark: '#0039B3', light: '#E6EEFF', bright: '#6EA8FF' },
        // Donkere secties / hero
        navy: { DEFAULT: '#0A0E27', deep: '#05071A', soft: '#141A3D' },
        // Tekst en vlakken
        ink: '#0A0B0D',
        softblue: '#F5F8FF',
        // Randen. 'field' (~3.3:1 op wit) voor interactieve besturing
        // (invoervelden, knoppen, checkboxes): haalt WCAG 1.4.11. 'line' is de
        // lichte decoratieve lijn voor kaarten, tabellen en scheidingen.
        field: '#868D9C',
        line: '#D7DEEC',
        // Statuskleuren dashboard
        status: {
          found: '#15803D', 'found-bg': '#F0FDF4',
          notfound: '#CF202F', 'notfound-bg': '#FEF2F2',
          error: '#6B7280', 'error-bg': '#F9FAFB',
        },
      },
      fontFamily: {
        sans: ['Montserrat', 'system-ui', '-apple-system', 'sans-serif'],
      },
      maxWidth: {
        prose: '46rem',
      },
    },
  },
};
