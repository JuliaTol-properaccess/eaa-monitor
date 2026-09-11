#!/usr/bin/env bash
#
# export-newsletter-kv.sh — exporteer de bevestigde nieuwsbrief-abonnees uit de
# Cloudflare KV-namespace NEWSLETTER, vlak voordat de oude Worker/KV/account
# worden opgeheven (EU-migratie, zie docs/eu-stack-migratie.md).
#
# Achtergrond: de sleutels staan als `sub:<e-mailadres>` in de namespace.
# Andere prefixen in dezelfde namespace (rl:, hof:) horen NIET in de export,
# vandaar het filter op prefix "sub:".
#
# Gotcha (zie newsletter-geheugen + docs/friction-log.md): `wrangler kv key`
# leest standaard de LOKALE simulatie. Zonder --remote krijg je een lege of
# verouderde lijst. Daarom staat --remote overal hieronder.
#
# Vereist: ingelogde wrangler (`npx wrangler login`) en jq.
# Draai vanuit de worker/-map:  bash export-newsletter-kv.sh

set -euo pipefail

NAMESPACE_ID="9bee247149b64408835caa8ca1761d18"   # binding NEWSLETTER (uit wrangler.jsonc)
PREFIX="sub:"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_JSON="newsletter-export-${STAMP}.json"        # volledige backup: sleutel + waarde
OUT_EMAILS="newsletter-emails-${STAMP}.txt"       # platte lijst e-mailadressen

command -v jq >/dev/null || { echo "jq ontbreekt: brew install jq"; exit 1; }

echo "Sleutels ophalen (prefix '${PREFIX}', --remote)..."
KEYS="$(npx wrangler kv key list \
          --namespace-id "${NAMESPACE_ID}" \
          --prefix "${PREFIX}" \
          --remote \
        | jq -r '.[].name')"

if [ -z "${KEYS}" ]; then
  echo "Geen abonnees gevonden. Sta je in de juiste account en is --remote actief?"
  exit 0
fi

COUNT="$(printf '%s\n' "${KEYS}" | wc -l | tr -d ' ')"
echo "Gevonden: ${COUNT} abonnee(s). Waarden ophalen..."

# E-mailadres = sleutel zonder de prefix; waarde bewaren we als backup.
printf '%s\n' "${KEYS}" | sed "s/^${PREFIX}//" | sort > "${OUT_EMAILS}"

echo "[" > "${OUT_JSON}"
first=1
while IFS= read -r key; do
  [ -z "${key}" ] && continue
  value="$(npx wrangler kv key get "${key}" \
             --namespace-id "${NAMESPACE_ID}" \
             --remote 2>/dev/null || true)"
  email="${key#${PREFIX}}"
  [ ${first} -eq 0 ] && echo "," >> "${OUT_JSON}"
  first=0
  jq -n --arg e "${email}" --arg v "${value}" \
        '{email:$e, value:$v}' >> "${OUT_JSON}"
done <<< "${KEYS}"
echo "]" >> "${OUT_JSON}"

echo
echo "Klaar:"
echo "  ${OUT_EMAILS}  (${COUNT} adressen, platte lijst)"
echo "  ${OUT_JSON}   (volledige backup met waarden)"
echo
echo "Bewaar beide buiten de repo (de repo is openbaar; geen e-mailadressen committen)."
