# Friction-log EAA Monitor

Bekende valkuilen bij externe API-calls, deploys en config. Check dit bestand
voordat je met Cloudflare, wrangler of e-mail aan de slag gaat. Voeg na afloop
nieuwe frictie toe met datum, context en oplossing.

## 2026-06-09 — wrangler `email sending list/dns get` geeft 2036 Unauthorized

**Context.** Na het verhuizen van `eaa-monitor.nl` naar Cloudflare wilden we de
verzendkant controleren met `npx wrangler email sending dns get eaa-monitor.nl`
en `... list`. Beide gaven `Unauthorized [code: 2036]`, terwijl `wrangler whoami`
wel `email_sending (write)` toonde en `wrangler deploy` gewoon werkte.

**Wat er aan de hand was.** Dit zijn **open-beta** commando's die op het
OAuth-login-token een autorisatiefout geven op het account-endpoint
`/accounts/.../email/sending/zones`. Het is een kink in de beta-CLI, geen
weerspiegeling van de echte staat van het domein.

**Hoe we het oplosten.** Niet de CLI vertrouwen maar de DNS zelf checken met
`dig`. De setup bleek volledig correct:
- MX: `route1/2/3.mx.cloudflare.net` (Email Routing, ontvangen)
- SPF: precies één record `v=spf1 include:_spf.mx.cloudflare.net ~all`
- DKIM: `cf2024-1._domainkey` met geldige `v=DKIM1; ...` sleutel (dit is de
  selector die Cloudflare Email Sending gebruikt, dus domein is onboarded)

`wrangler deploy` toonde daarna `env.EMAIL (unrestricted)`, wat bevestigt dat de
Worker naar willekeurige ontvangers mag versturen.

**Vermijd voortaan.** Draai `email sending enable` niet nog eens "voor de zekerheid"
als de DKIM/SPF-records al staan, dat kan records dubbel zetten. Verifieer de staat
met `dig` (MX, TXT voor SPF, TXT op `cf2024-1._domainkey`), niet met de beta-CLI.
Wil je de beta-commando's tóch laten werken, dan heb je een API-token met
expliciete Email-permissies nodig in plaats van de OAuth-login.
