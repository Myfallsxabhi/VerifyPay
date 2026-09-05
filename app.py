"""
AI Invoice/Receipt Auditor
--------------------------
Upload a messy invoice (text, or paste raw text), and the AI:
  1. Extracts structured line items (item, qty, unit price, total)
  2. Cross-checks totals for math errors
  3. Flags anomalies (duplicate line items, missing tax, suspiciously
     round numbers, mismatched totals, missing vendor/date info)
  4. Produces a plain-English summary of what a human reviewer should
     double check before approving payment.

Run with:
    streamlit run app.py

Requires a free Gemini API key set as the environment variable
GEMINI_API_KEY (see README.md for how to get one — no credit card
needed).
"""

import json
import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # reads a .env file in this folder, if present, into os.environ

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-2.5-flash"  # fast + free-tier, good enough for structured extraction

SYSTEM_PROMPT = """You are an expert accounts-payable auditor. You will be given
the raw, possibly messy text of an invoice or receipt (it may come from a
scanned PDF, so formatting can be broken, spacing weird, or OCR artifacts
present).

Your job:
1. Extract structured data: vendor name, invoice number, date, line items
   (description, quantity, unit price, line total), subtotal, tax, and
   grand total. If a field is missing, use null.
2. Recompute the math yourself: does quantity * unit price = line total?
   Does the sum of line totals + tax = grand total? Note any mismatches.
3. Flag anomalies you notice, such as:
   - Duplicate line items (same description appearing twice)
   - Suspiciously round numbers (e.g. exactly 1000.00 with no cents)
   - Missing tax on an otherwise taxable-looking purchase
   - Missing vendor name, date, or invoice number
   - Math that doesn't add up
   - Prices that look implausible for the item described
4. Write a short, plain-English summary (2-4 sentences) a human reviewer
   can read in 10 seconds to decide whether to approve, hold, or reject
   this invoice for payment.

Respond ONLY with valid JSON matching this exact schema, no markdown
fences, no commentary outside the JSON:

{
  "vendor": string or null,
  "invoice_number": string or null,
  "date": string or null,
  "line_items": [
    {"description": string, "quantity": number or null, "unit_price": number or null, "line_total": number or null}
  ],
  "subtotal": number or null,
  "tax": number or null,
  "grand_total": number or null,
  "math_check": {"line_items_match": boolean, "total_matches": boolean, "notes": string},
  "anomalies": [string],
  "risk_level": "low" | "medium" | "high",
  "summary": string
}
"""


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "No GEMINI_API_KEY found. Set it as an environment variable "
            "before running the app (see README.md)."
        )
        st.stop()
    return genai.Client(api_key=api_key)


def audit_invoice(raw_text: str) -> dict:
    """Send raw invoice text to the LLM and get back structured audit JSON."""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"Here is the invoice text:\n\n{raw_text}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Invoice Auditor", page_icon="🧾", layout="wide")

st.title("🧾 AI Invoice / Receipt Auditor")
st.caption(
    "Paste messy invoice text below (or load a sample). The AI extracts "
    "structured data, re-checks the math, and flags anything a human "
    "reviewer should look at twice."
)

sample_dir = os.path.join(os.path.dirname(__file__), "sample_invoices")
sample_files = sorted(os.listdir(sample_dir)) if os.path.isdir(sample_dir) else []

col_a, col_b = st.columns([3, 1])
with col_b:
    chosen_sample = st.selectbox("Load a sample invoice", ["-- none --"] + sample_files)
    load_clicked = st.button("Load sample", use_container_width=True)

if "invoice_text" not in st.session_state:
    st.session_state.invoice_text = ""

if load_clicked and chosen_sample != "-- none --":
    with open(os.path.join(sample_dir, chosen_sample), "r") as f:
        st.session_state.invoice_text = f.read()

with col_a:
    invoice_text = st.text_area(
        "Raw invoice / receipt text",
        value=st.session_state.invoice_text,
        height=280,
        placeholder="Paste raw invoice text here (copy-paste from a PDF, email, OCR output, etc.)",
    )

run = st.button("🔍 Audit this invoice", type="primary")

if run:
    if not invoice_text.strip():
        st.warning("Paste some invoice text first, or load a sample.")
        st.stop()

    with st.spinner("Reading the invoice and checking the math..."):
        try:
            result = audit_invoice(invoice_text)
        except Exception as e:
            st.error(f"Something went wrong calling the AI: {e}")
            st.stop()

    risk = result.get("risk_level", "unknown")
    risk_color = {"low": "green", "medium": "orange", "high": "red"}.get(risk, "gray")

    st.markdown(f"### Risk level: :{risk_color}[{risk.upper()}]")
    st.info(result.get("summary", "No summary returned."))

    left, right = st.columns(2)

    with left:
        st.subheader("Extracted details")
        st.write(f"**Vendor:** {result.get('vendor') or '—'}")
        st.write(f"**Invoice #:** {result.get('invoice_number') or '—'}")
        st.write(f"**Date:** {result.get('date') or '—'}")
        st.write(f"**Subtotal:** {result.get('subtotal')}")
        st.write(f"**Tax:** {result.get('tax')}")
        st.write(f"**Grand total:** {result.get('grand_total')}")

        st.subheader("Line items")
        line_items = result.get("line_items", [])
        if line_items:
            st.table(line_items)
        else:
            st.write("No line items extracted.")

    with right:
        st.subheader("Math check")
        math_check = result.get("math_check", {})
        st.write(f"Line items add up correctly: **{math_check.get('line_items_match')}**")
        st.write(f"Grand total matches: **{math_check.get('total_matches')}**")
        if math_check.get("notes"):
            st.caption(math_check["notes"])

        st.subheader("⚠️ Anomalies flagged")
        anomalies = result.get("anomalies", [])
        if anomalies:
            for a in anomalies:
                st.write(f"- {a}")
        else:
            st.write("None flagged. Looks clean.")

    with st.expander("Raw JSON (for debugging / architecture demo)"):
        st.json(result)
