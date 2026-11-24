// crisp-discord-tagger.js
// -----------------------------------------------------------------------------
// Purpose: automatically tag Tako/"Discord Tickets" conversations in Crisp with a
// "discord" segment, so your existing sub-inbox rule (segment = "discord") routes
// every ticket -- even though each Tako thread has a unique channel ID.
//
// Flow:
//   Crisp webhook (new activity) -> this service -> is it a Discord/Tako convo?
//   -> if yes, add "discord" segment via Update Conversation Metas -> your
//   sub-inbox rule does the routing.
//
// Requires Node 18+ (global fetch).
//   npm init -y && npm install express
//   node crisp-discord-tagger.js
//
// You must supply credentials via environment variables (see below). This file
// never contains secrets -- generate a Crisp *plugin token* (identifier + key)
// in the Crisp Marketplace and set them in your host's env, not in code.
// -----------------------------------------------------------------------------

require("dotenv").config();
const express = require("express");
const crypto = require("crypto");

const {
  CRISP_IDENTIFIER,       // plugin token identifier  (generate in Crisp Marketplace)
  CRISP_KEY,              // plugin token key          (generate in Crisp Marketplace)
  CRISP_WEBSITE_ID,       // your Crisp website id (set in env)
  CRISP_WEBHOOK_SECRET,   // the secret you set when registering the webhook
  PORT = 3000,
} = process.env;

const API = "https://api.crisp.chat/v1";
const AUTH =
  "Basic " + Buffer.from(`${CRISP_IDENTIFIER}:${CRISP_KEY}`).toString("base64");
const HEADERS = {
  Authorization: AUTH,
  "X-Crisp-Tier": "plugin",
  "Content-Type": "application/json",
};

const app = express();
app.use(express.json());

app.post("/crisp-webhook", async (req, res) => {
  // 1) Verify the request actually came from Crisp.
  //    Per Crisp's own node-crisp-api (__verifySignature), the signed string is
  //    "[" + timestamp + ";" + JSON.stringify(parsedBody) + "]" -- the
  //    re-serialized parsed body, not the raw request bytes.
  if (CRISP_WEBHOOK_SECRET) {
    const sig = req.get("X-Crisp-Signature") || "";
    const timestamp = req.get("X-Crisp-Request-Timestamp") || "";
    const signedString = `[${timestamp};${JSON.stringify(req.body)}]`;
    const expected = crypto
      .createHmac("sha256", CRISP_WEBHOOK_SECRET)
      .update(signedString)
      .digest("hex");
    const sigBuf = Buffer.from(sig, "hex");
    const expectedBuf = Buffer.from(expected, "hex");
    const valid =
      sigBuf.length === expectedBuf.length &&
      crypto.timingSafeEqual(sigBuf, expectedBuf);
    if (!valid) return res.status(401).end();
  }

  // Acknowledge immediately so Crisp doesn't retry; then do the work.
  res.status(200).end();

  try {
    // Discovery aid: set DEBUG=1 to print the real webhook headers + body once,
    // so you can confirm the signature header name and where "urn:discord" lives.
    // Turn DEBUG off once you've confirmed everything.
    if (process.env.DEBUG) {
      console.log("--- webhook headers ---\n", JSON.stringify(req.headers, null, 2));
      console.log("--- webhook body ---\n", JSON.stringify(req.body, null, 2));
    }

    const { website_id, data } = req.body || {};
    const sessionId = data && data.session_id;
    if (!website_id || !sessionId) return;
    await tagIfDiscord(website_id, sessionId);
  } catch (e) {
    console.error("handler error:", e);
  }
});

async function tagIfDiscord(websiteId, sessionId) {
  // 2) Fetch the conversation to inspect where it originated.
  const conv = await api(`/website/${websiteId}/conversation/${sessionId}`);
  const meta = (conv && conv.data && conv.data.meta) || {};

  // 3) Decide if it's a Tako/Discord conversation.
  //    VERIFY THE FIELD: inspect ONE real conversation payload and confirm where
  //    the "urn:discord:..." value actually lives. It may be meta.origin,
  //    conv.data.channel, or similar. Adjust this line to match reality.
  const origin = String(meta.origin || (conv && conv.data && conv.data.channel) || "");
  const isDiscord = origin.startsWith("urn:discord");
  if (!isDiscord) return;

  // 4) Merge segments (don't clobber existing ones), add "discord", be idempotent.
  const segments = new Set(meta.segments || []);
  if (segments.has("discord")) return; // already tagged; nothing to do
  segments.add("discord");

  await api(
    `/website/${websiteId}/conversation/${sessionId}/meta`,
    "PATCH",
    { segments: [...segments] }
  );
  console.log(`tagged ${sessionId} -> discord`);
}

async function api(path, method = "GET", body) {
  const r = await fetch(API + path, {
    method,
    headers: HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    throw new Error(`${method} ${path} -> ${r.status} ${await r.text()}`);
  }
  return r.json();
}

app.listen(PORT, () =>
  console.log(`listening on :${PORT} (POST /crisp-webhook)`)
);
