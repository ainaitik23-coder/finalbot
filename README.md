# Instagram AI Bot

Auto-replies to Instagram DMs using Gemini/Groq (with fallback), LangGraph-style
orchestration (kept as plain async functions for simplicity — swap in real
LangGraph later if you want branching logic), FastAPI webhook, and SQLite memory.

## 1. Meta / Instagram setup (do this first, before running any code)

1. Convert your Instagram account to a **Professional (Business/Creator) account**
   in the Instagram app settings.
2. Go to [developers.facebook.com](https://developers.facebook.com) → create an App
   → add the **Instagram** product.
3. Under Instagram → API setup, link your Instagram professional account.
4. Generate a **Page Access Token** (long-lived) — this goes in `.env` as
   `IG_PAGE_ACCESS_TOKEN`.
5. Note your **App Secret** (App Settings → Basic) — goes in `.env` as `IG_APP_SECRET`.
6. Choose any random string yourself for `IG_VERIFY_TOKEN` (you invent this, Meta
   doesn't give it to you) — used only during webhook verification.
7. **Don't set the webhook URL in Meta's dashboard yet** — you need your server
   deployed and running first (see below), because Meta immediately sends a GET
   request to verify the URL when you save it.

In **Development Mode**, the app works for your own linked Instagram account
without needing App Review — good enough for personal/testing use.

## 2. Local setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# now fill in .env with your real values
```

## 3. Run locally (for testing with ngrok)

```bash
uvicorn app.main:app --reload --port 8000
```

In another terminal:
```bash
ngrok http 8000
```

Use the `https://xxxx.ngrok-free.app` URL as your webhook URL in the Meta
dashboard, callback URL = `<that-url>/webhook`, verify token = whatever you put
in `.env`. Subscribe to the `messages` field.

## 4. Deploy for real 24/7 uptime (with persistent memory)

Your laptop sleeping will break this — you need an always-on server. But free
compute hosts (Render, Koyeb, etc.) don't keep local files across restarts,
which would wipe `memory/chat.db`. Fix: keep the database external.

**Recommended combo:**
- **Koyeb** (free instance) for running the app — sleeps after 1 hour of no
  traffic (better than Render's 15 min), wakes automatically on the next
  message.
- **Supabase** (free Postgres, 500MB) for the database — persists forever,
  independent of the app's sleep/restart cycle.

Steps:
1. Create a free Supabase project, grab its Postgres connection string
   (`postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres`).
2. Set `DATABASE_URL` in your deployment's environment variables to that
   string as-is — the code auto-converts it to the asyncpg driver format.
3. Push this repo to GitHub, create a Koyeb Web Service from it, instance
   type "Free", add all your `.env` variables (including the Supabase
   `DATABASE_URL`) in Koyeb's Environment Variables section.
4. Build command: `pip install -r requirements.txt`.
   Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Once deployed, update the Callback URL in Meta's Webhooks page to your
   Koyeb URL + `/webhook`.

(Render is a fine alternative to Koyeb if you prefer it — same steps, just a
shorter sleep timeout of 15 minutes.)

## 5. Customize the bot's personality

Edit `prompts/persona.txt` — plain text, no code changes needed. `prompts/system.txt`
holds the core behavior rules and `prompts/safety.txt` holds hard boundaries —
edit carefully, don't remove the safety file.

## 6. Multiple API keys (rotation)

You can list as many keys as you want per provider in `.env`:

```
GEMINI_API_KEYS=key1,key2,key3,key4,key5
GROQ_API_KEYS=keyA,keyB,keyC
```

No hard limit on count, and you can add more later by editing `.env` and
restarting the process. Order is fixed: **all Gemini keys first (left to
right), then all Groq keys.**

Behavior:
- Every reply uses the next available key in that order.
- If a key hits its rate limit (HTTP 429), it's put on a 24h cooldown and the
  very next message immediately uses the next key - no interruption, same
  conversation, same memory.
- Once a key's cooldown expires it automatically becomes available again.
- If **every single key across both providers** is currently rate-limited,
  the bot replies with a fixed message instead of erroring out:
  `*kal baat karte hain ham aapse, abhi hamara thoda kaam chal raha hai*`
  (edit `ALL_KEYS_EXHAUSTED_MESSAGE` in `app/ai/llm.py` if you want to change
  this wording).

## 7. Notes

- `memory/chat.db` is created automatically on first run (SQLite).
- Logs go to `logs/app.log` (all) and `logs/errors.log` (errors only).
- Gemini/Groq both have free tiers with rate limits — the router in
  `app/ai/router.py` falls back from your `DEFAULT_PROVIDER` to the other one
  automatically if a call fails.
- This has not been tested against a live Meta webhook yet — the webhook
  verification step (Step 3) is where you'll find out if signature/token setup
  is correct. Check `logs/errors.log` if replies aren't sending.
