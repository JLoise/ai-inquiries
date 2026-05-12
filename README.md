# SMC Enquiry Processor

> AI-powered client enquiry triage tool for Strata Management Consultants.

Paste any client enquiry — the tool classifies it, scores AI confidence, suggests a
draft reply, recommends a staff action, and routes it to the right team, all in under
two seconds.

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- A free [Gemini API key](https://aistudio.google.com/apikey) (Google AI Studio — free tier available)

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Set your API key

```bash
# macOS / Linux
export GEMINI_API_KEY="AIza..."

# Windows (PowerShell)
$env:GEMINI_API_KEY = "AIza..."
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
python3 cli.py "Hi, my levy notice looks wrong — the amount doubled this quarter."

# Pipe from stdin
echo "Water is leaking through the ceiling above unit 4." | python3 cli.py
```

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
| **Classification** | 8 categories: new client, support, complaint, billing, maintenance, legal, general, unclear |
| **Confidence scoring** | 0–100 % with a plain-English explanation of certainty |
| **Sentiment detection** | positive / neutral / negative / urgent |
| **Routing** | Each category maps to a team, SLA, and priority level |
| **Draft response** | Professional, ready-to-send reply (editable) |
| **Escalation flag** | Auto-raised for urgent, safety-related, or legal-threat enquiries |
| **Key points** | 2–5 action items for the handling staff member |
| **Error handling** | Graceful fallback for API failures, malformed JSON, empty inputs |

---

## Prompt Engineering Design Choices

### Structured JSON output

The system prompt asks Gemini to return *only* valid JSON with a fixed schema.
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
| `GEMINI_API_KEY` | *(required)* | Gemini API key |
| `PORT` | `5000` | Web server port |

The model is set to `gemini-2.0-flash` in `app.py`. Change `MODEL` to swap.

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
