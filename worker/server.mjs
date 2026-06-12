/**
 * Node-adapter voor de bezwaar-Worker op de VPS (EU-stack, zie docs/server.md).
 *
 * Draait exact dezelfde src/index.js als op Cloudflare, maar dan als gewone
 * Node-service achter Caddy (pad /api/*, poort 8787). De Cloudflare-specifieke
 * randen worden hier nagebootst:
 *   - KV-namespace NEWSLETTER  -> JSON-bestand met TTL (KV_FILE)
 *   - CF-Connecting-IP         -> eerste IP uit X-Forwarded-For (gezet door Caddy)
 *   - request.url              -> interne URL; links in mails gebruiken
 *                                 PUBLIC_BASE_URL (zie publicBase in src/index.js)
 *
 * Configuratie via environment (systemd EnvironmentFile=/etc/eaa-forms.env).
 * Starten: node server.mjs
 */

import { createServer } from "node:http";
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import worker from "./src/index.js";

const PORT = parseInt(process.env.PORT || "8787", 10);
const KV_FILE = process.env.KV_FILE || "/var/lib/eaa-forms/kv.json";

/** Minimale KV-shim met dezelfde semantiek als Cloudflare KV voor zover de
 * Worker die gebruikt: get -> string|null, put met expirationTtl, delete.
 * Volume is klein (nieuwsbrief + rate-limit-tellers), dus een JSON-bestand
 * met atomische writes volstaat. */
class FileKV {
  constructor(file) {
    this.file = file;
    mkdirSync(dirname(file), { recursive: true });
    try {
      this.data = JSON.parse(readFileSync(file, "utf-8"));
    } catch {
      this.data = {};
    }
  }
  _save() {
    const tmp = this.file + ".tmp";
    writeFileSync(tmp, JSON.stringify(this.data));
    renameSync(tmp, this.file);
  }
  _prune() {
    const now = Date.now();
    for (const [k, v] of Object.entries(this.data)) {
      if (v.expiresAt && v.expiresAt <= now) delete this.data[k];
    }
  }
  async get(key) {
    const entry = this.data[key];
    if (!entry) return null;
    if (entry.expiresAt && entry.expiresAt <= Date.now()) {
      delete this.data[key];
      this._save();
      return null;
    }
    return entry.value;
  }
  async put(key, value, opts = {}) {
    this._prune();
    this.data[key] = {
      value: String(value),
      ...(opts.expirationTtl ? { expiresAt: Date.now() + opts.expirationTtl * 1000 } : {}),
    };
    this._save();
  }
  async delete(key) {
    delete this.data[key];
    this._save();
  }
  // Zelfde vorm als Cloudflare KV's list(): { keys: [{name}], list_complete }.
  // Gebruikt door GET /hof/votes (prefix hof:count:). Het volume blijft klein,
  // dus alles in één pagina; een cursor is niet nodig.
  async list(opts = {}) {
    this._prune();
    const prefix = opts.prefix || "";
    const keys = Object.keys(this.data)
      .filter((k) => k.startsWith(prefix))
      .sort()
      .map((name) => ({ name }));
    return { keys, list_complete: true };
  }
}

const env = { ...process.env, NEWSLETTER: new FileKV(KV_FILE) };

const server = createServer(async (req, res) => {
  try {
    const headers = new Headers();
    for (const [k, v] of Object.entries(req.headers)) {
      if (typeof v === "string") headers.set(k, v);
      else if (Array.isArray(v)) headers.set(k, v.join(", "));
    }
    // Rate limiter verwacht het Cloudflare-header; Caddy levert X-Forwarded-For.
    const xff = req.headers["x-forwarded-for"];
    if (xff && !headers.has("cf-connecting-ip")) {
      headers.set("CF-Connecting-IP", String(xff).split(",")[0].trim());
    }
    const hasBody = req.method !== "GET" && req.method !== "HEAD";
    const request = new Request(`http://127.0.0.1:${PORT}${req.url}`, {
      method: req.method,
      headers,
      ...(hasBody ? { body: req, duplex: "half" } : {}),
    });
    const response = await worker.fetch(request, env);
    res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (err) {
    console.error("Onverwachte fout:", err);
    res.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
    res.end("Er ging iets mis. Probeer het later opnieuw.");
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`eaa-forms luistert op 127.0.0.1:${PORT}, KV: ${KV_FILE}`);
});
