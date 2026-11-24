# GTM work sample: Tonishqa Kaplish

Two production systems I built and ran as Marketing Technology Lead at Flatiron School. Both were live and people relied on them daily. This is a redacted copy, published as a code sample.

| Folder | What it is | Stack | Ran on |
|---|---|---|---|
| [`roster-sync/`](roster-sync/) | Hourly sync of enrolled students from Close CRM, plus a partner college's sheet, into the shared student roster | Python, Close API, Google Sheets API | GitHub Actions (hourly cron) |
| [`crisp-discord-tagger/`](crisp-discord-tagger/) | Webhook service that labels Discord tickets in Crisp so no-code routing and the AI agent can handle them | Node.js, Express, Crisp REST API | Always-on web service |

## roster-sync

```
Close CRM (opportunities, leads, custom objects, ledger activities) ─┐
                                                                      ├─▶ transform ─▶ upsert by key ─▶ roster sheet (owned columns only)
Partner college sheet (immersive students) ───────────────────────────┘
```

- `extract.py`: pages through Close, keeps the most recent enrollment per student, and joins contact, application state and the latest tuition ledger
- `transform.py`: maps Close wording to the roster's exact dropdown values. Unknown values pass through, so no student is dropped
- `immersive.py`: second source, keyed on a hash of the email, so re-runs stay idempotent
- `load.py`: matches columns by header name and writes only the 13 columns the sync owns. Renamed headers are skipped and reported, never overwritten
- `.github/workflows/sync.yml`: hourly schedule, secrets in GitHub, and a `DRY_RUN` switch

Run: `pip install -r requirements.txt`, set `CLOSE_API_KEY`, `GOOGLE_SA_JSON`, `ROSTER_SHEET_ID` (and optionally `IMMERSIVE_SHEET_ID`), then `python main.py`. `DRY_RUN` defaults to true.

## crisp-discord-tagger

Crisp webhook ▶ HMAC signature check ▶ 200 ack ▶ fetch conversation ▶ if it's from `urn:discord`, merge a `discord` segment (idempotent) ▶ Crisp's no-code rules route it and the AI agent answers.

Run: `npm install`, set `CRISP_IDENTIFIER`, `CRISP_KEY`, `CRISP_WEBSITE_ID`, `CRISP_WEBHOOK_SECRET`, then `npm start`. The full setup guide I wrote for the team is in `SETUP-crisp-discord-tagger.md`.

## What I redacted

- Close CRM custom field, custom object and activity type IDs (replaced with `*_REDACTED`)
- The Crisp website ID (it's now a required environment variable)
- The partner college's name (now "Partner")
- No credentials, sheet IDs or student data were ever in the code. Secrets lived in environment variables and GitHub Secrets
- Commit history is not included
