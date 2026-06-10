# Server: eaa-monitor-1 (Hetzner Cloud)

*Aangemaakt 10 juni 2026 als onderdeel van de EU-stack-migratie (zie `eu-stack-migratie.md`).*

## Gegevens

| | |
|---|---|
| **Naam** | eaa-monitor-1 |
| **IP** | 128.140.50.96 |
| **Type** | CX23 (2 vCPU, 4 GB RAM, 40 GB disk), €3,99/mnd incl. btw |
| **Locatie** | Falkenstein, Duitsland (fsn1) |
| **OS** | Ubuntu 24.04 LTS |
| **Beheer** | console.hetzner.cloud, project "Default" |

## Toegang

```bash
ssh -i ~/.ssh/eaa_monitor_ed25519 root@128.140.50.96
```

De sleutel `eaa_monitor_ed25519` staat op Julia's Mac in `~/.ssh/` en als "eaa-monitor-deploy" in de Hetzner Console (Security → SSH keys). Het Hetzner-API-token staat in `.env` (`HCLOUD_TOKEN`).

## Stack

- **Caddy** (webserver): config in `/etc/caddy/Caddyfile`, site-root `/var/www/eaa-monitor`. Draait nu op poort 80 (test via IP); bij de DNS-verhuizing wordt het siteadres `eaa-monitor.nl` en regelt Caddy zelf TLS.
- **Node 22**: voor de formulieren-service (Worker-vervanger) op poort 8787, achter Caddy via het pad `/api/*`.
- **UFW-firewall**: alleen SSH (22), HTTP (80) en HTTPS (443) open.

## Deploy van de site

```bash
rsync -az --delete -e "ssh -i ~/.ssh/eaa_monitor_ed25519" public/ root@128.140.50.96:/var/www/eaa-monitor/
rsync -az -e "ssh -i ~/.ssh/eaa_monitor_ed25519" data/ root@128.140.50.96:/var/www/eaa-monitor/data/
```

Let op: `--delete` alleen op de `public/`-sync, niet op `data/`.

## Caddy herladen na een configwijziging

```bash
ssh -i ~/.ssh/eaa_monitor_ed25519 root@128.140.50.96 "caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy"
```

## Formulieren-service (eaa-forms)

Draait dezelfde code als de Cloudflare Worker (`worker/src/index.js`) via de
Node-adapter `worker/server.mjs`, als systemd-service `eaa-forms` op poort
8787, achter Caddy op het pad `/api/*`.

- **Code:** `/opt/eaa-forms/` (rsync vanaf de repo: `worker/src`, `worker/server.mjs`, `worker/package.json`)
- **Config/secrets:** `/etc/eaa-forms.env` (chmod 600; SIGNING_SECRET, BREVO_API_KEY; GITHUB_TOKEN nog toevoegen vóór de DNS-verhuizing)
- **Opslag:** `/var/lib/eaa-forms/kv.json` (nieuwsbrief + rate-limit-tellers)
- **Logs:** `journalctl -u eaa-forms`
- **Herstarten na code-update:** `systemctl restart eaa-forms`

Deploy van een nieuwe versie:

```bash
rsync -az -e "ssh -i ~/.ssh/eaa_monitor_ed25519" worker/src worker/server.mjs worker/package.json root@128.140.50.96:/opt/eaa-forms/
ssh -i ~/.ssh/eaa_monitor_ed25519 root@128.140.50.96 "systemctl restart eaa-forms"
```
