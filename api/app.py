"""
Strata Management Enquiry Processor
Uses Google Gemini API to classify and respond to client enquiries.
"""

import os
import json
import re
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import openai
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

app = Flask(__name__, template_folder='../templates')

# Rate limiting configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["50 per minute"],
    strategy="moving-window"
)

# ---------------------------------------------------------------------------
# OpenRouter client – key is read from the OPENROUTER_API_KEY env variable
# ---------------------------------------------------------------------------
client = openai.OpenAI(api_key=os.environ.get("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
MODEL = "google/gemma-3-27b-it"

# ---------------------------------------------------------------------------
# Enquiry categories and routing rules (single source of truth)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "new_client":        {"label": "New Client Enquiry",   "team": "Sales & Onboarding",   "sla": "Same day",    "priority": "high"},
    "support_request":   {"label": "Support Request",      "team": "Property Management",  "sla": "4 hours",     "priority": "high"},
    "complaint":         {"label": "Complaint",            "team": "Client Relations",     "sla": "2 hours",     "priority": "urgent"},
    "billing_finance":   {"label": "Billing / Finance",    "team": "Accounts",             "sla": "1 business day","priority": "medium"},
    "maintenance":       {"label": "Maintenance Request",  "team": "Facilities",           "sla": "4 hours",     "priority": "high"},
    "legal_compliance":  {"label": "Legal / Compliance",   "team": "Legal",                "sla": "Same day",    "priority": "urgent"},
    "general_question":  {"label": "General Question",     "team": "Front Office",         "sla": "Next business day","priority": "low"},
    "unclear":           {"label": "Unclear / Spam",       "team": "Front Office",         "sla": "Review manually","priority": "low"},
}

# ---------------------------------------------------------------------------
# Prompt engineering
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert enquiry triage assistant for Strata Management Consultants (SMC),
a 100% independent Melbourne-based advisory service for owners corporations and Committee members.

SMC works with Committees and for Committees. Your output should reflect that the company helps OC Committees:
- change body corporate / strata management companies
- resolve poor manager performance, communication failures, and service gaps
- understand levy notices, by-laws, AGMs, legal compliance and defect management
- obtain records and reports from existing managers

Your job is to analyse incoming client enquiries and return a structured JSON object.

## Classification categories (use exactly one key):
- new_client        — prospective OC/Committee enquiry about changing managers, independent advice, fees, service providers, or onboarding with SMC
- support_request   — existing Committee member needing help with records, documents, minutes, inspections, or ongoing strata management issues
- complaint         — frustrated owner or Committee member reporting poor service, unresponsiveness, contract issues, or threats to escalate
- billing_finance   — invoices, levies, special levies, budgets, financial statements, fees, or cost breakdowns
- maintenance       — building defects, repairs, water ingress, structural issues, inspections, or facilities work
- legal_compliance  — by-laws, AGM/EGM notices, disputes, insurance, legislation, Committee liability, or compliance questions
- general_question  — miscellaneous strata questions that do not fit the above categories
- unclear           — spam, gibberish, or so vague classification is impossible

## Output format — respond with ONLY valid JSON, no markdown fences, no extra text:
{
  "category": "<key from list above>",
  "confidence": <float 0.0–1.0>,
  "confidence_reason": "<one sentence explaining your certainty level>",
  "sentiment": "<positive|neutral|negative|urgent>",
  "summary": "<1–2 sentence neutral summary of the enquiry>",
  "key_points": ["<point 1>", "<point 2>", ...],
  "suggested_response": "<professional, empathetic draft reply the staff member can send verbatim or edit>",
  "recommended_action": "<concrete next step for the staff member>",
  "escalate": <true|false>,
  "escalation_reason": "<if escalate is true, briefly explain why, otherwise null>"
}

## Guidelines:
- suggested_response must be 3–6 sentences, warm yet professional, signed "SMC Client Services"
- Prefer language that reassures Committees and owners corporations the enquiry will be handled independently and with expert strata advice
- If confidence < 0.6, set category to "unclear" and explain in confidence_reason
- escalate = true if the message contains urgency (flood, fire, safety risk, legal threat, very angry tone)
- key_points should be 2–5 clear action items for the staff member
- recommended_action should identify the next step for an OC Committee or staff member handling a strata-related request
- Never fabricate specifics (addresses, names, amounts) not present in the enquiry
"""

def analyse_enquiry(text: str) -> dict:
    """Send the enquiry to OpenRouter and parse the structured response."""
    start = time.time()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Please analyse the following client enquiry and return your JSON response:\n\n<enquiry>\n{text.strip()}\n</enquiry>"}
            ]
        )
        raw = (response.choices[0].message.content or "").strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        elapsed = round(time.time() - start, 2)

        # Enrich with routing metadata
        meta = CATEGORIES.get(result.get("category", "unclear"), CATEGORIES["unclear"])
        result.update({
            "team":            meta["team"],
            "sla":             meta["sla"],
            "priority":        meta["priority"],
            "category_label":  meta["label"],
            "processing_time": elapsed,
            "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model":           MODEL,
            "error":           None,
        })
        return result

    except json.JSONDecodeError as e:
        return _error_response(f"AI returned malformed JSON: {e}", text)
    except Exception as e:
        msg = str(e)
        print(f"[API Error] {msg}")  # Log full error
        if "API_KEY" in msg or "api key" in msg.lower() or "credentials" in msg.lower():
            return _error_response("Invalid or missing API key. Set OPENROUTER_API_KEY correctly.", text)
        if "quota" in msg.lower() or "rate" in msg.lower() or "429" in msg or "resource_exhausted" in msg.lower():
            return _error_response("Gemini API quota exceeded. Upgrade your plan or wait for quota reset.", text)
        if "connect" in msg.lower() or "network" in msg.lower():
            return _error_response("Could not reach the Gemini API. Check your network.", text)
        return _error_response(msg, text)


def _error_response(message: str, original_text: str) -> dict:
    meta = CATEGORIES["unclear"]
    return {
        "category":        "unclear",
        "category_label":  meta["label"],
        "confidence":      0.0,
        "confidence_reason": "An error prevented analysis.",
        "sentiment":       "neutral",
        "summary":         "Unable to process enquiry.",
        "key_points":      [],
        "suggested_response": "Thank you for reaching out to Strata Management Consultants. We have received your enquiry and will be in touch shortly.",
        "recommended_action": "Review enquiry manually — automated analysis failed.",
        "escalate":        False,
        "escalation_reason": None,
        "team":            meta["team"],
        "sla":             meta["sla"],
        "priority":        meta["priority"],
        "processing_time": 0,
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model":           MODEL,
        "error":           message,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyse", methods=["POST"])
@limiter.limit("50 per minute")
def analyse():
    data = request.get_json(silent=True) or {}
    text = (data.get("enquiry") or "").strip()

    if not text:
        return jsonify({"error": "No enquiry text provided."}), 400
    if len(text) > 5000:
        return jsonify({"error": "Enquiry too long (max 5 000 characters)."}), 400

    result = analyse_enquiry(text)
    return jsonify(result)


@app.route("/categories")
@limiter.limit("200 per minute")
def categories():
    return jsonify(CATEGORIES)


@app.route("/health")
@limiter.limit("100 per minute")
def health():
    return jsonify({"status": "ok", "model": MODEL})


# Export for Vercel
application = app