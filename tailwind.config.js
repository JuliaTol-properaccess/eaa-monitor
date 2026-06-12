/*
 * Gedeelde Tailwind-configuratie voor de hele EAA Hub.
 * Eén bron van waarheid voor kleuren en typografie.
 *
 * Na een wijziging hier of in de gebruikte classes:
 *   npm run build:css
 *
 * Designrichting: "De Telling" (zie docs/rebranding/rebranding-voorstel.md).
 * Warm papier, groen als merk- én doelkleur, okergeel als telmarker.
 * De oude tokennamen (brand/navy/softblue) blijven bestaan als alias zodat
 * bestaande classes blijven werken; nieuwe componenten gebruiken de
 * Nederlandse namen (papier/inkt/loofgroen/dennengroen/oker).
 */
const palet = {
  papier: '#FAF7F1',
  zachtgroen: '#E9F2EA',
  inkt: '#20281F',
  steungrijs: '#46524B',
  loofgroen: '#1A5632',
  hovergroen: '#123E23',
  dennengroen: '#0D2B1F',
  oker: '#F4C84B',
};

module.exports = {
  content: [
    "./public/**/*.html",
    "./public/**/*.js",
    "./tools/*.py", // HTML-templates in Python-strings (build-tools en scraper)
  ],
  theme: {
    extend: {
      colors: {
        ...palet,
        // Aliassen voor bestaande classes. 'bright' is de accentkleur op
        // donkere achtergronden (okergeel: 9,56:1 op dennengroen).
        brand: { DEFAULT: palet.loofgroen, dark: palet.hovergroen, light: palet.zachtgroen, bright: palet.oker },
        // Donkere secties / callouts / footer
        navy: { DEFAULT: palet.dennengroen, deep: '#081F16', soft: '#16382A' },
        // Tekst en vlakken
        ink: palet.inkt,
        softblue: palet.zachtgroen,
        // Randen. 'field' (3,9:1 op wit) voor interactieve besturing
        // (invoervelden, knoppen, selects): haalt WCAG 1.4.11. 'line' is de
        // zachte decoratieve rand voor kaarten, tabellen en scheidingen.
        field: '#76847A',
        line: '#C8D2C9',
        // Statuskleuren dashboard (status communiceert nooit met kleur
        // alleen: altijd icoon/bol + tekstlabel ernaast)
        status: {
          found: '#1C6B3C', 'found-bg': '#EAF4EC',
          notfound: '#B3261E', 'notfound-bg': '#FBEDEB',
          error: '#5B6560', 'error-bg': '#F2F4F1',
        },
        // Warme groengrijze neutralen i.p.v. de koele Tailwind-grays die
        // her en der in classes staan (tekst, hovers, placeholders).
        gray: {
          50: '#F6F4EE',
          100: '#EFECE3',
          200: '#DDE2DC',
          300: '#C8D2C9',
          400: '#6E7A72',
          500: '#535F57',
          600: '#46524B',
          700: '#39443D',
          800: '#2B342E',
          900: '#20281F',
        },
      },
      fontFamily: {
        sans: ['Atkinson Hyperlegible', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Fraunces Variable', 'Georgia', 'Times New Roman', 'serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      maxWidth: {
        prose: '46rem',
      },
    },
  },
};
