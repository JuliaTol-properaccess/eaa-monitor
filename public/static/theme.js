/*
 * Gedeelde Tailwind-configuratie voor de hele EAA Hub.
 * Eén bron van waarheid voor kleuren en typografie. Wordt geladen NA de
 * Tailwind CDN-play-script op elke pagina (handmatig en gegenereerd).
 *
 * Designrichting: Coinbase-look. Bewust losgemaakt van het Proper Access-merk
 * (magenta/petrol). Proper Access blijft in de footer-attributie en schema.
 */
tailwind.config = {
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
