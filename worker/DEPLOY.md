# Bezwaar-Worker uitrollen

Deze Cloudflare Worker verwerkt bezwaren tegen vermelding grotendeels
automatisch. De misbruikbescherming zit in domein-verificatie: een bezwaar wordt
alleen automatisch ingediend als iemand op het webshop-domein zelf de
bevestigingslink aanklikt. Na bevestiging opent de Worker een pull request, die
Julia met één klik goedkeurt. Past het e-mailadres niet bij het webshop-domein,
dan krijgt Julia een mail en verwerkt ze het bezwaar handmatig volgens
`workflows/handle_objection.md`.

## Flow

```
bezwaar.html  ──POST /submit──▶  Worker
                                   │
                  e-maildomein == webshopdomein?
                   ja │                       │ nee
                      ▼                       ▼
        bevestigingsmail naar         mail naar Julia
        het webshop-adres             (handmatige check)
                      │
        gebruiker klikt de link
                      ▼
              GET /confirm  ──▶  branch + commit + pull request op objections.json
                      ▼
              Julia merget de PR  ──▶  deploy.yml draait  ──▶  webshop verdwijnt
```

## Eenmalige setup

### 1. Dependencies

```bash
cd worker
npm install
npx wrangler login
```

### 2. E-mailverzending aanzetten voor het domein

Het `FROM_EMAIL`-domein (`eaa-monitor.nl`) moet onboarden bij Cloudflare Email
Sending. Dit kan alleen als `eaa-monitor.nl` als zone in je Cloudflare-account
staat (DNS via Cloudflare beheerd).

```bash
npx wrangler email sending enable eaa-monitor.nl
npx wrangler email sending dns get eaa-monitor.nl   # controleer SPF + DKIM
```

Staat `eaa-monitor.nl` niet bij Cloudflare? Twee opties:
- Verhuis de DNS van `eaa-monitor.nl` naar Cloudflare (de site blijft op GitHub
  Pages staan, alleen de naamservers wijzigen), of
- gebruik tijdelijk een ander Cloudflare-domein als afzender en pas `FROM_EMAIL`
  in `wrangler.jsonc` aan.

### 3. GitHub-token aanmaken

Maak een **fine-grained personal access token**:
- Repository access: alleen `JuliaTol-properaccess/eaa-monitor`
- Permissions: **Contents → Read and write** en **Pull requests → Read and write**
- Looptijd: zo kort als praktisch is, met een herinnering om te verversen

### 4. Secrets zetten

```bash
# Willekeurige sterke string, bv. uit: openssl rand -hex 32
npx wrangler secret put SIGNING_SECRET

# De fine-grained PAT uit stap 3
npx wrangler secret put GITHUB_TOKEN
```

### 5. Deployen

```bash
npx wrangler deploy
```

Wrangler toont de Worker-URL, bijvoorbeeld
`https://eaa-bezwaar.<jouw-subdomein>.workers.dev`. De bevestigingslink in de
mail wijst automatisch naar `/confirm` op ditzelfde adres, dus je hoeft niets
extra's te configureren. Wil je een net adres (bv. `bezwaar.eaa-monitor.nl`),
voeg dan een Worker-route of custom domain toe in het Cloudflare-dashboard.

### 6. Frontend koppelen

Zet in `public/bezwaar.html` de constante `BEZWAAR_ENDPOINT` op de
`/submit`-URL van de Worker:

```js
const BEZWAAR_ENDPOINT = "https://eaa-bezwaar.<jouw-subdomein>.workers.dev/submit";
```

Zolang die leeg is, blijft het formulier via Formspree naar Julia mailen, dus de
site blijft werken tot je klaar bent om de Worker live te zetten. Commit en push
deze wijziging pas als de Worker draait.

## Testen

1. **Lokaal** (stuurt echte mail, gebruik een eigen testadres):
   ```bash
   cd worker
   # tijdelijk "remote": true bij send_email in wrangler.jsonc voor echte mail
   npx wrangler dev
   ```
   Test met een webadres en e-mailadres op hetzelfde domein dat je beheert.

2. **Domeinmatch** (auto-route): vul een webadres in en een e-mailadres op
   datzelfde domein. Je hoort een bevestigingsmail te krijgen; na klikken opent
   er een pull request op de repo met de nieuwe entry in `data/objections.json`.

3. **Geen match** (handmatige route): vul een gmail-adres in. Julia krijgt een
   notificatiemail, er wordt geen PR aangemaakt.

4. **Dubbel klikken**: klik de bevestigingslink twee keer. De tweede keer meldt
   de pagina dat het verzoek al is ingediend. Geen tweede PR.

## Logs

```bash
cd worker
npx wrangler tail
```

## Aandachtspunten / beperkingen

- **E-mailbommen voorkomen.** Iemand kan `/submit` herhaaldelijk aanroepen met
  een webshop-adres en zo bevestigingsmails naar dat domein laten sturen. Zet in
  Cloudflare een **Rate Limiting Rule** op het pad `/submit` (bv. max 5 per
  minuut per IP).
- **eTLD-lijst is beperkt.** De domeinvergelijking dekt `.nl`, `.com`, `.be` en
  een korte lijst tweelaagse TLD's (`co.uk` enz.), geen volledige public-suffix-
  lijst. Twijfelgevallen vallen veilig terug op de handmatige route.
- **Token is stateless.** De bevestigingslink draagt zelf alle gegevens, getekend
  met `SIGNING_SECRET`. Roteer dat secret als je vermoedt dat het gelekt is; alle
  openstaande links vervallen dan.
- **Merge triggert deploy.** De Worker pusht niet naar `main`, maar opent een PR.
  Zodra jij die merget (een push door jou, niet door Actions' `GITHUB_TOKEN`),
  draait `deploy.yml` en is het dashboard meestal binnen enkele minuten bij.
- **Branch-opruiming.** Zet in de repo-instellingen "Automatically delete head
  branches" aan, dan ruimt GitHub de `bezwaar/...`-branches na de merge op.
