# SMC Enquiry Processor

> AI-powered enquiry triage for Strata Management Consultants, tailored to owners corporations and OC Committees in Melbourne.

This tool helps SMC staff process Committee and owner enquiries by classifying strata-related requests, scoring AI confidence, recommending routing, and drafting a professional response.

It is designed for the specific context of independent strata advisory work: changing body corporate managers, Committee support, levy inquiries, by-law and legal compliance, and defect / maintenance issues.

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- An OpenRouter API key for the configured model

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Set your API key

```bash
# macOS / Linux
export OPENROUTER_API_KEY="your_openrouter_api_key"

# Windows (PowerShell)
$env:OPENROUTER_API_KEY = "your_openrouter_api_key"
```

### 4a. Run the web UI

```bash
python3 app.py
```

Open **http://localhost:5000** in your browser.

### 4b. Run the CLI

```bash
# Interactive mode (type enquiry, press Enter twice)
python3 cli.py

# Single enquiry from command line
python3 cli.py "Our Committee needs independent advice on changing our strata manager and reviewing levy notices."

# Pipe from stdin
echo "The current body corporate manager has not provided AGM minutes in a month." | python3 cli.py

### 4c. Deploy to Vercel

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   vercel
   ```

3. Set environment variable in Vercel dashboard:
   - Go to your project in Vercel dashboard
   - Settings → Environment Variables
   - Add `OPENROUTER_API_KEY` with your OpenRouter API key

4. Redeploy if needed:
   ```bash
   vercel --prod
   ```

The app will be available at your Vercel URL.

---

## API Rate Limiting

The API endpoints are protected with rate limiting using a moving window strategy (sliding window):

- **`/analyse`** (POST): 50 requests per minute - Main enquiry processing endpoint
- **`/categories`** (GET): 200 requests per minute - Category definitions
- **`/health`** (GET): 100 requests per minute - Health check endpoint

Rate limits are applied per IP address. When exceeded, the API returns a 429 (Too Many Requests) response.

---

## Project Structure

```
enquiry-processor/
├── app.py              # Flask app + AI analysis logic
├── cli.py              # Command-line interface
├── requirements.txt
├── README.md
└── templates/
    └── index.html      # Single-page web UI
```

---

## Features

| Feature | Detail |
|---|---|
| **Classification** | 8 categories for Committee and strata enquiries: new client, support, complaint, billing, maintenance, legal, general, unclear |
| **Confidence scoring** | 0–100 % with a plain-English explanation of certainty |
| **Sentiment detection** | positive / neutral / negative / urgent |
| **Routing** | Each category maps to an SMC team, SLA, and priority level |
| **Draft response** | Professional, Committee-friendly reply template with warm tone |
| **Escalation flag** | Auto-raised for urgent safety, legal, or highly dissatisfied enquiries |
| **Key points** | 2–5 action items that Committee-facing staff need to act on |
| **Error handling** | Graceful fallback for API failures, malformed JSON, empty inputs |

---

## Prompt Engineering Design Choices

### Structured JSON output

The system prompt asks the AI model to return *only* valid JSON with a fixed schema.
This avoids post-processing fragility. A regex strip removes occasional markdown
code fences the model sometimes adds despite instructions.

### Explicit category taxonomy

Eight named keys (not free-text labels) prevent near-duplicate categories and make
downstream routing deterministic. The model is given concrete examples in comments.

### Confidence < 0.6 → "unclear"

Rather than forcing a low-confidence classification, the prompt instructs the model
to self-report uncertainty and fall back to "unclear" — which routes to a human
reviewer rather than auto-responding incorrectly.

### Escalation logic in the prompt

The escalation flag is defined by semantic signals ("flood, fire, safety risk, legal
threat, very angry tone") rather than keyword matching. This catches paraphrased
urgency that a regex would miss.

### Tone calibration

The suggested_response constraint ("3–6 sentences, warm yet professional, signed SMC
Client Services") prevents both terse one-liners and over-long responses, and keeps
all AI-generated replies on-brand.

---

## Automation Potential

This prototype is designed to slot into a larger workflow:

```
Inbound email / web form
        │
        ▼
  [Webhook / Parser]          parse raw email into plain text
        │
        ▼
  app.py  analyse_enquiry()   AI triage (this tool)
        │
        ▼
  ┌─────────────────────────────────────────────────────┐
  │  result dict                                         │
  │  • category + team  → CRM queue / ticket assignment  │
  │  • priority         → SLA timer start                │
  │  • escalate=true    → immediate Slack/Teams alert     │
  │  • suggested_reply  → draft in staff email client     │
  └─────────────────────────────────────────────────────┘
        │
        ▼
  Staff reviews & sends        human in the loop
```

Integration points:
- **Email**: Connect to an IMAP/SMTP server (e.g. via `imaplib`) or a service like
  SendGrid Inbound Parse to feed raw emails into `analyse_enquiry()`.
- **Web form**: POST the form body directly to `/analyse`.
- **CRM**: Map `category + team` to ticket types in Salesforce, HubSpot, or Zoho.
- **Task queue**: Push high-priority results to a Celery/RQ queue for async handling.
- **Alerting**: If `escalate == true`, fire a Slack webhook immediately.

---

## API Reference (web mode)

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/` | GET | — | Web UI |
| `/analyse` | POST | `{"enquiry": "..."}` | Full analysis JSON |
| `/categories` | GET | — | Category metadata |
| `/health` | GET | — | `{"status":"ok"}` |

---

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | OpenRouter API key |
| `PORT` | `5000` | Web server port |

The model is set in `app.py` using the `MODEL` constant. Change `MODEL` to switch to a different OpenRouter-compatible model.

---

## Error Handling

| Situation | Behaviour |
|---|---|
| Empty input | 400 response + clear message |
| Input > 5 000 chars | 400 response |
| Invalid API key | Graceful error card, no crash |
| Rate limit hit | User-friendly message, retry prompt |
| Network failure | Fallback "unclear" result with error note |
| Malformed AI JSON | Caught, logged, fallback result returned |
| Vague / nonsense input | Classified as "unclear", confidence < 0.6 |
