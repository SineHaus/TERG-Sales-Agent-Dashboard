# Rental Inquiry Sales Agent

An email assistant for a tent and event rental business. When a customer emails your Gmail, it:

1. Reads the inquiry and pulls out the event details (date, guest count, venue, surface, tent, tables, chairs and more).
2. Writes a friendly reply asking for whatever is still missing and saves it in **Gmail Drafts**. Nothing is sent without you.
3. Keeps going as the customer replies, until everything needed for a quote is collected.
4. Shows every lead on a **dashboard** with the full conversation, the info collected, and a copy-ready block laid out in Goodshuffle Pro's order.

You build and send the quote in Goodshuffle Pro yourself, then mark the lead "Quote sent".

## Lead statuses

| Status | Meaning |
|---|---|
| Collecting info | The agent is still asking for required details |
| Ready to quote | All required details are in. Build the quote in Goodshuffle |
| Needs you | Discounts, urgent dates (within 7 days), complaints, anything unusual. A polite holding reply is drafted |
| Quote sent / Booked / Lost | You set these. If a customer writes back after a quote, the lead returns to "Needs you" |
| Not an inquiry | Newsletters, vendors, receipts. Hidden from the main list |

## Setup (about 20 minutes)

You need Python 3.10 or newer.

### 1. Install

```bash
cd sales-agent
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### 2. Add your settings

```bash
cp .env.example .env
```

Open `.env` and fill in your business name, your first name (used to sign the emails), your service area, and your Claude API key. You can create a key at https://platform.claude.com under **Settings → API keys**.

`BUSINESS_NOTES` is where you tell the agent anything it should know, such as delivery radius, lead times or permit rules. The agent never quotes prices.

### 3. Try it before connecting Gmail (optional)

```bash
python seed_demo.py
```

```bash
python run.py
```

Open http://localhost:5000. You'll see three sample leads. Click **Try it** to paste a sample customer email and watch the agent respond. Remove the samples later with `python seed_demo.py --clear`.

### 4. Connect Gmail

You only do this once. It lets the app read your inbox and create drafts.

1. Go to https://console.cloud.google.com and create a project (any name, e.g. "Sales Agent").
2. Open **APIs & Services → Library**, search for **Gmail API**, and click **Enable**.
3. Open **APIs & Services → OAuth consent screen**. Choose **External** (or **Internal** if you use Google Workspace), fill in the app name and your email, and under **Test users** add the Gmail address that receives your inquiries.
4. Open **APIs & Services → Credentials → Create credentials → OAuth client ID**, choose **Desktop app**, then **Download JSON**.
5. Save that file as `credentials.json` inside the `sales-agent` folder.
6. Run:

```bash
python connect_gmail.py
```

A browser window opens. Sign in and allow access. You may see "Google hasn't verified this app": click **Continue**, since this is your own app.

7. Start the agent:

```bash
python run.py
```

It checks Gmail every 2 minutes. You can also click **Check now** on the dashboard.

## Daily use

- **Gmail:** Draft replies appear in the customer's email thread. Review them and press send.
- **Dashboard:** Open a lead to see the conversation, edit the draft and click **Send reply**, fix any field the agent got wrong, or add private notes under **Steer the agent** (for example "We're booked that day, offer Sunday") and have it rewrite the draft.
- **Goodshuffle Pro:** When a lead is **Ready to quote**, click **Copy all** in the "For Goodshuffle Pro" panel and enter the details into a new project.

## Customizing

- **Which fields to collect:** edit `fields.py`. Fields marked `True` are required before a lead is "Ready to quote".
- **Tone and rules:** edit `SYSTEM_PROMPT` in `agent.py`.
- **Which emails it looks at:** `GMAIL_QUERY` in `.env` uses Gmail search syntax. For example, `in:inbox label:inquiries` if you already filter inquiries into a label, or `to:info@yourbiz.com`.

## Running it 24/7 on Render

The agent only works while it's running, so for always-on use, host it. This repo includes a Render setup (`render.yaml`). Render's Starter plan (about $7/month, plus about $0.25/month for the 1 GB disk that keeps your leads) stays on around the clock. The free plan goes to sleep and would stop checking Gmail.

**Before you start:** do the Gmail connection step above on your own computer once (`python connect_gmail.py`). That creates a `token.json` file. The server can't open a browser to sign in, so you'll paste that file's contents into Render.

**Important Google setting:** in Google Cloud, open **APIs & Services → OAuth consent screen** and click **Publish app** (set it to "In production"). While an app is in "Testing", Google expires its sign-in after 7 days and the agent would stop seeing new email. You don't need Google's verification for your own account. You'll just see the "unverified app" notice once when signing in. If you're on Google Workspace and chose **Internal**, skip this.

1. Create an account at https://render.com and connect your GitHub.
2. Click **New → Blueprint** and choose this repository. Render reads `render.yaml`.
3. Fill in the values it asks for:
   - `ANTHROPIC_API_KEY`: your Claude API key
   - `DASHBOARD_PASSWORD`: a strong password. Required, since the dashboard is on the internet
   - `GMAIL_TOKEN_JSON`: open `token.json` in a text editor and paste the whole contents
   - `BUSINESS_NAME`, `OWNER_NAME`, `SERVICE_AREA`, `BUSINESS_NOTES`: same as in `.env`
4. Click **Apply**. After a few minutes, your dashboard is live at the `onrender.com` address Render shows. Sign in with your password.

Changes you push to GitHub redeploy automatically. To change settings later, go to your service in Render → **Environment**.

**If Gmail stops syncing** (for example, you changed your Google password): run `python connect_gmail.py` on your computer again, then in Render open **Shell** and run `rm /var/data/token.json`, update `GMAIL_TOKEN_JSON` with the new `token.json` contents, and redeploy.

**Other hosts:** the `Procfile` works on Railway, Heroku and similar hosts. Give it a persistent volume, set `DATA_DIR` to that volume's path, set `ON_SERVER=true`, and set the same variables as above. Always run a single worker, as in the Procfile.

## Costs and privacy

- The agent uses Claude (`claude-opus-5-5`) and costs a few cents per email it handles. Newsletters and promotions are filtered out by the default Gmail search before Claude sees them.
- Data stays in a local file (`sales_agent.db`). Email text is sent to the Claude API only to process each inquiry.
- The agent is told to treat email content as customer data and not to follow instructions written inside emails. Because every reply is a draft you approve, a strange email can't make it send anything on its own.
