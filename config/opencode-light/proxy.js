"use strict";
// Logging proxy: opencode -> here -> Ollama (local, cloud, weave) or the
// PrismML llama.cpp server (hf). Logs the full chat request (messages + tools)
// and response (assistant text + tool calls) to stdout, so it shows up in
// `docker compose logs opencode`. Routes by /local, /cloud, /weave or /hf prefix.
// The auth header is forwarded but never logged.
const http = require("http");
const https = require("https");
const { URL } = require("url");

const PORT = parseInt(process.env.CHAT_LOG_PORT || "8787", 10);
const MAXLEN = parseInt(process.env.CHAT_LOG_MAXLEN || "6000", 10); // per field; 0 = unlimited
const UPSTREAMS = {
  local: process.env.UPSTREAM_LOCAL || "http://ollama:11434",
  cloud: process.env.UPSTREAM_CLOUD || "https://ollama.com",
  weave: process.env.UPSTREAM_WEAVE || "https://weave.redpencil.io",
  hf:    process.env.UPSTREAM_HF    || "http://huggingface-local:8080",
};

const ts = () => new Date().toISOString();
const trunc = (s) => (MAXLEN > 0 && s.length > MAXLEN) ? s.slice(0, MAXLEN) + ` ...[+${s.length - MAXLEN} chars]` : s;

function logReq(key, method, path, body) {
  if (!/\/chat\/completions/.test(path)) {
    console.log(`[chat-log ${ts()}] ${key} ${method} ${path} (${body.length}b)`);
    return;
  }
  let p; try { p = JSON.parse(body.toString()); } catch { console.log(`[chat-log] ${key} chat: <unparseable ${body.length}b>`); return; }
  console.log(`\n===== ${ts()}  REQUEST -> ${key} / ${p.model || "?"} =====`);
  for (const m of p.messages || []) {
    const c = typeof m.content === "string" ? m.content : JSON.stringify(m.content);
    console.log(`  [${m.role}] ${trunc(c)}`);
    if (m.tool_calls) console.log(`    tool_calls: ${trunc(JSON.stringify(m.tool_calls))}`);
  }
  if (Array.isArray(p.tools) && p.tools.length) console.log(`  (tools: ${p.tools.map((t) => t.function && t.function.name).join(", ")})`);
}

function logResp(key, status, headers, body) {
  const ct = headers["content-type"] || "";
  const text = body.toString();
  console.log(`----- ${ts()}  RESPONSE <- ${key} (${status}) -----`);
  if (ct.includes("event-stream") || text.startsWith("data:")) {
    let content = ""; const tools = [];
    for (const line of text.split("\n")) {
      const t = line.trim();
      if (!t.startsWith("data:")) continue;
      const d = t.slice(5).trim();
      if (!d || d === "[DONE]") continue;
      try {
        const j = JSON.parse(d);
        const delta = (j.choices && j.choices[0] && j.choices[0].delta) || {};
        if (delta.content) content += delta.content;
        if (delta.tool_calls) tools.push(...delta.tool_calls);
      } catch { /* skip non-JSON data line */ }
    }
    if (content) console.log(`  [assistant] ${trunc(content)}`);
    if (tools.length) console.log(`    tool_calls: ${trunc(JSON.stringify(tools))}`);
    if (!content && !tools.length) console.log(`  <stream, ${body.length}b, no text parsed>`);
  } else {
    try {
      const j = JSON.parse(text);
      const m = (j.choices && j.choices[0] && j.choices[0].message) || {};
      if (m.content) console.log(`  [assistant] ${trunc(m.content)}`);
      if (m.tool_calls) console.log(`    tool_calls: ${trunc(JSON.stringify(m.tool_calls))}`);
      if (!m.content && !m.tool_calls) console.log("  " + trunc(text));
    } catch { console.log("  " + trunc(text)); }
  }
  console.log(`==========================================\n`);
}

const server = http.createServer((req, res) => {
  const match = req.url.match(/^\/(local|cloud|weave|hf)(\/.*)?$/);
  if (!match) { res.writeHead(404); res.end("route must start with /local, /cloud, /weave or /hf"); return; }
  const key = match[1];
  const path = match[2] || "/";
  const up = new URL(UPSTREAMS[key]);
  const mod = up.protocol === "https:" ? https : http;

  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("error", (e) => console.error("[chat-log] req error:", e.message));
  req.on("end", () => {
    const reqBody = Buffer.concat(chunks);
    try { logReq(key, req.method, path, reqBody); } catch (e) { console.error("[chat-log] logReq:", e.message); }

    const headers = Object.assign({}, req.headers, { host: up.host });
    delete headers["accept-encoding"]; // keep responses uncompressed so we can read them
    const upReq = mod.request({
      protocol: up.protocol, hostname: up.hostname,
      port: up.port || (up.protocol === "https:" ? 443 : 80),
      path, method: req.method, headers,
    }, (upRes) => {
      const rh = Object.assign({}, upRes.headers);
      delete rh["transfer-encoding"]; delete rh["connection"]; delete rh["content-encoding"];
      res.writeHead(upRes.statusCode, rh);
      const out = [];
      upRes.on("data", (c) => { out.push(c); res.write(c); }); // tee: forward live + collect for logging
      upRes.on("end", () => { res.end(); try { logResp(key, upRes.statusCode, upRes.headers, Buffer.concat(out)); } catch (e) { console.error("[chat-log] logResp:", e.message); } });
    });
    upReq.on("error", (e) => { console.error("[chat-log] upstream error:", e.message); if (!res.headersSent) res.writeHead(502); res.end("upstream error: " + e.message); });
    upReq.end(reqBody);
  });
});

process.on("uncaughtException", (e) => console.error("[chat-log] uncaught:", e.message));
server.listen(PORT, "0.0.0.0", () => console.log(`[chat-log] proxy on :${PORT} (local -> ${UPSTREAMS.local}, cloud -> ${UPSTREAMS.cloud}, weave -> ${UPSTREAMS.weave}, hf -> ${UPSTREAMS.hf}) maxlen=${MAXLEN}`));
