# Setup: Auto-tag Discord tickets so Hugo can handle them

**What you're building, in one breath:** a tiny always-on program that watches Crisp
for new Discord tickets and stamps each one with a `discord` label. Once that label
is on the conversation, Crisp's own no-code tools do the rest — route it to the
Discord inbox *and* let the AI Agent (Hugo) answer it. You write no code for the
last part; the program only exists to apply the label, because Crisp has no
no-code way to do that for Tako conversations.

**The pieces:**

```
New Discord ticket ─▶ Crisp fires a "webhook" ─▶ your program ─▶ adds "discord" label
                                                                        │
                        ┌───────────────────────────────────────────────┘
                        ▼
        (no code) sub-inbox rule: label = discord ──▶ ticket lands in Discord inbox
        (no code) workflow: label = discord ──▶ "Answer with Hugo"
```

You'll do this in 8 phases. Budget an afternoon the first time. Phases 3 and 5 are
where the real thinking is; the rest is mechanical.

---

## Vocabulary (30 seconds)

- **Webhook** — a message Crisp automatically sends to a web address you own, every
  time something happens (like a new ticket). Your program listens for these.
- **Environment variable ("env var")** — a secret setting (like a password) you give
  your program *outside* the code, so secrets never live in the code itself.
- **Plugin token** — the username + password your program uses to talk to Crisp's
  API. Two parts: an *identifier* and a *key*.
- **Deploy / host** — put your program on a computer that's always on (not your
  laptop), so it can receive webhooks 24/7.

---

## Phase 1 — Get the program onto your computer

1. **Install Node.js** (the thing that runs the program). Go to <https://nodejs.org>,
   download the "LTS" version, install it with all defaults.
2. **Check it worked.** Open Terminal (Mac) or Command Prompt (Windows) and type:
   ```
   node -v
   ```
   You should see a version number like `v20.x`. Any number 18 or higher is fine.
3. **Make a folder** for the project and put `crisp-discord-tagger.js` inside it.
   In the terminal, navigate into that folder:
   ```
   cd path/to/your/folder
   ```
4. **Set up the project** (creates a settings file and installs the one library
   the program needs):
   ```
   npm init -y
   npm install express
   ```
   You now have a `node_modules` folder and a `package.json`. Don't worry about them.

---

## Phase 2 — Get your Crisp credentials (the plugin token)

1. Go to the **Crisp Marketplace**: <https://marketplace.crisp.chat>. Sign in with
   your Crisp account.
2. Create a new **plugin** (or "private plugin" / "token"). Give it a name like
   `Discord Tagger`.
3. Under its **permissions/scopes**, grant it the ability to **read and write
   conversations** (it needs to read a conversation to check where it came from, and
   write to add the label). If you see specific scopes, you want conversation read +
   conversation meta write.
4. Find its **production token**: an **identifier** and a **key**. Copy both
   somewhere safe (a password manager).

> **Rule:** these two values are secrets. They never go in the code and never get
> committed to GitHub. They only go into env vars (Phase 4). If either ever leaks,
> regenerate them in the Marketplace.

---

## Phase 3 — Find the ONE real value the code is guessing at

The program needs to recognize a Discord ticket. It does that by looking for
`urn:discord` in the conversation's data — but I don't know exactly *which field*
holds it in your account. Confirm it now with a single command; takes two minutes.

1. In Crisp, open one of your **existing Discord tickets** in the inbox.
2. Look at the browser address bar. The URL ends in something like
   `.../inbox/session_733242ef-be1d-...`. Copy that **`session_...`** part — that's
   the conversation's ID.
3. In your terminal, run this, pasting in your identifier, key, and session id
   (keep the quotes):
   ```
   curl "https://api.crisp.chat/v1/website/YOUR_WEBSITE_ID/conversation/SESSION_ID_HERE" \
     -u "IDENTIFIER_HERE:KEY_HERE" \
     -H "X-Crisp-Tier: plugin"
   ```
   (`-u` handles the login for you; no need to encode anything.)
4. A blob of JSON prints out. **Search it for `urn:discord`.** Note what the field is
   called and where it sits. Common possibilities: `meta.origin`, or a top-level
   `channel`.
5. Open `crisp-discord-tagger.js`, find the line commented **"VERIFY THE FIELD"**, and
   make sure it reads from the field you just found. The default already tries
   `meta.origin` and `channel`; if yours is different, adjust it. If it's one of
   those two, you're done — leave it.

> If the command errors with 401/403, your token scopes are wrong or the
> identifier/key is mistyped — fix that before moving on.

---

## Phase 4 — Put the program online (so it's always on)

Your laptop can't receive webhooks reliably. We'll host it free on **Render**. (Any
host works — Railway, Fly, a small cloud VM — but Render is the most click-driven.)

1. **Make a GitHub account** if you don't have one (<https://github.com>), and create
   a **new empty repository**. Before pushing, add a file named `.gitignore`
   containing this one line so you never upload junk or secrets:
   ```
   node_modules
   ```
2. **Push your folder** to that repo. If you've never used git, GitHub's "upload
   files" button on the repo page works fine for a first time — upload
   `crisp-discord-tagger.js`, `package.json`, and `.gitignore`. **Do not upload your
   token or any secrets.**
3. Go to <https://render.com>, sign in with GitHub, click **New ▸ Web Service**, and
   pick your repo.
4. Settings:
   - **Runtime:** Node
   - **Build command:** `npm install`
   - **Start command:** `node crisp-discord-tagger.js`
5. Add your **environment variables** (this is where the secrets go — safely, not in
   the code):
   | Name | Value |
   |------|-------|
   | `CRISP_IDENTIFIER` | your plugin identifier |
   | `CRISP_KEY` | your plugin key |
   | `CRISP_WEBSITE_ID` | `YOUR_WEBSITE_ID` |
   | `DEBUG` | `1`  *(temporary — for Phase 5; remove later)* |
6. Click **Create Web Service**. When it finishes, Render shows a public URL like
   `https://discord-tagger-xxxx.onrender.com`. Copy it.

> Free Render services "sleep" after inactivity and take a few seconds to wake on the
> first request. Fine for testing. For real student traffic, upgrade to a paid
> always-on instance so the first ticket after a quiet spell isn't delayed.

---

## Phase 5 — Connect Crisp's webhook to your program

1. In Crisp, go to **Settings ▸ (Website) ▸ Web Hooks** (or the webhook section of
   your plugin in the Marketplace).
2. Add a webhook pointing at your Render URL **with `/crisp-webhook` on the end**:
   ```
   https://discord-tagger-xxxx.onrender.com/crisp-webhook
   ```
3. **Choose which events to send.** You want the one that fires when a *new
   conversation/message* arrives (e.g. `message:received`). Pick the minimum that
   catches new tickets — you don't need everything.
4. Crisp will give you a **signing secret** (a value used to prove the webhook really
   came from Crisp). Copy it and add it as another env var in Render:
   | Name | Value |
   |------|-------|
   | `CRISP_WEBHOOK_SECRET` | the signing secret from Crisp |
5. **Confirm the signature works** (this is the one security-critical check). Because
   `DEBUG=1` is on, open a test ticket in Discord, then look at your Render **logs**
   (Render dashboard ▸ your service ▸ Logs). You'll see the webhook's headers and
   body printed. Find:
   - the header that carries the signature (the code assumes `X-Crisp-Signature` —
     confirm the real name and update the code if it differs), and
   - confirm the body has a `website_id` and `data.session_id`.
   Match the code's signature check to what Crisp actually sends. If the signatures
   don't line up, the code rejects the webhook (401) — fix the header name / scheme
   until a real Crisp webhook passes.

> **Do not leave the endpoint live without working signature verification.** Without
> it, anyone who finds your URL can POST fake events. Get the check passing, then
> continue.

6. Once confirmed, **set `DEBUG` to `0`** (or delete it) in Render so you're not
   logging conversation contents. Redeploy.

---

## Phase 6 — Test that the label gets applied

1. Open a **brand-new ticket** in your test Discord server, post a message.
2. In Crisp, open that conversation and check its **segments/labels** — it should now
   show `discord`. (Render logs will also print `tagged <session> -> discord`.)
3. Open a **second** new ticket and confirm it *also* gets tagged. This is the whole
   point — every ticket, despite each having a different thread ID, gets the same
   stable `discord` label.

If tagging works, the hard part is done. Everything below is no-code.

---

## Phase 7 — Wire the no-code parts (routing + Hugo)

Now that every Discord ticket carries the `discord` label, use Crisp's built-in
tools — no more coding.

**A) Route them into the Discord inbox**
1. Settings ▸ Inbox Settings ▸ Sub-Inboxes ▸ **Discord**.
2. Change its condition from "Conversation channel" to match **segment = `discord`**.
3. Save. (This replaces the broken exact-match-on-channel rule.)

**B) Let Hugo answer them**
1. Open your **workflow** (the one you were building).
2. **Entry Gate / condition:** segment **is** `discord`.
3. **Action:** **Answer with Hugo**.
4. Save.

> **Live-workspace safety:** scope this workflow tightly to `segment = discord` and
> nothing broader. This is your real workspace with live admissions conversations —
> a loose condition could make Hugo start answering real admissions chats. Test with
> the Discord test server before trusting it.

---

## Phase 8 — Full end-to-end test

1. Post a new question in a Discord ticket.
2. Watch it: (a) appear in Crisp, (b) get the `discord` label, (c) land in the Discord
   sub-inbox, (d) get a reply from Hugo, (e) that reply show up back in the Discord
   thread.
3. If all five happen, you're done — Discord is a self-serve channel.

> Reminder: Hugo answers *from the Knowledge Base*. Until the student KB is populated,
> Hugo will answer Discord tickets from whatever content exists (currently admissions).
> The pipeline you just built is correct and ready; the quality of the answers depends
> on the KB being filled in.

---

## Quick reference — all env vars

| Name | What it is | Where it comes from |
|------|-----------|--------------------|
| `CRISP_IDENTIFIER` | token username | Crisp Marketplace (Phase 2) |
| `CRISP_KEY` | token password | Crisp Marketplace (Phase 2) |
| `CRISP_WEBSITE_ID` | which workspace | already known: `YOUR_WEBSITE_ID` |
| `CRISP_WEBHOOK_SECRET` | proves webhooks are real | Crisp webhook settings (Phase 5) |
| `DEBUG` | extra logging (temporary) | you set `1`, then remove (Phase 5–6) |

## If something breaks

- **Nothing gets tagged:** is the webhook actually reaching Render? Check Render logs
  for incoming requests. If none, the webhook URL or events are wrong (Phase 5).
- **Webhook rejected (401 in logs):** signature check mismatch — re-check the header
  name and secret (Phase 5.5).
- **401/403 when tagging:** token scopes too narrow, or identifier/key wrong (Phase 2).
- **Tagged but not routing:** the sub-inbox is still on the old channel rule — switch
  it to segment (Phase 7A).
