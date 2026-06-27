// Genereert data/axe-rules.json: welke axe-core-regels meetellen (WCAG A/AA)
// en welke bewust worden uitgesloten (best-practice zoals landmarks, plus AAA).
// Draaien: node tools/gen_axe_rules.js
const axe = require('./vendor/axe.min.js');
const fs = require('fs');
const path = require('path');

const WCAG_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22a', 'wcag22aa'];

function scTag(tags) {
  const t = tags.find((x) => /^wcag\d{3,4}$/.test(x));
  if (!t) return '';
  const n = t.replace('wcag', '');
  return n.length === 3 ? `${n[0]}.${n[1]}.${n[2]}` : `${n[0]}.${n[1]}.${n.slice(2)}`;
}

const enabled = [];
const bestPractice = [];
const other = [];
for (const r of axe.getRules()) {
  const row = { id: r.ruleId, sc: scTag(r.tags), desc: r.description, help: r.helpUrl, tags: r.tags };
  if (r.tags.some((t) => WCAG_AA.includes(t))) enabled.push(row);
  else if (r.tags.includes('best-practice')) bestPractice.push(row);
  else other.push(row);
}

const out = path.join(__dirname, '..', 'data', 'axe-rules.json');
fs.writeFileSync(
  out,
  JSON.stringify({ axe_version: axe.version, wcag_aa_tags: WCAG_AA, enabled, best_practice: bestPractice, other }, null, 2)
);
console.log(`axe ${axe.version}: ${enabled.length} WCAG A/AA, ${bestPractice.length} best-practice, ${other.length} overig -> ${out}`);
