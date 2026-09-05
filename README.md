# VerifyPay

**Track:** Open Track — Razorpay AI Buildathon 2026

## The problem

Accounts-payable teams get invoices in every messy format imaginable —
scanned PDFs, OCR'd receipts, copy-pasted email text. Someone has to
manually re-check the math, spot duplicate charges, and catch missing
tax or vendor details before approving payment. It's tedious and easy
to get wrong when you're tired or rushing.

## What this does

You paste in raw invoice text (however messy). The AI:

1. Extracts structured data — vendor, invoice number, date, line
   items, subtotal, tax, grand total.
2. Recomputes the math itself — does `qty × unit_price` match the
   line total? Does everything sum to the grand total?
3. Flags anomalies — duplicate line items, suspiciously round
   numbers, missing tax, missing vendor/date, implausible prices.
4. Gives a plain-English verdict(low / medium / high risk) a
   human can read in 10 seconds to decide: approve, hold, or reject.

## Architecture

```
User pastes invoice text
        │
        ▼
  Streamlit UI (app.py)
        │
        ▼
  Gemini API call (gemini-2.5-flash, free tier)
  — system prompt instructs the model to act as an
    accounts-payable auditor and return strict JSON
        │
        ▼
  JSON parsed and rendered as:
    - extracted fields
    - line item table
    - math check
    - anomaly list
    - risk level + summary
```

No training, no fine-tuning, no vector database — just a well-designed
prompt, structured output (JSON mode), and a UI that makes the AI's
reasoning legible to a human reviewer. This keeps the system simple,
fast to build, and easy to explain to a technical panel.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get a **free** Gemini API key (no credit card required):
   - Go to https://aistudio.google.com/apikey
   - Sign in with a Google account
   - Click "Create API key"
   - Copy the key

3. Save your key permanently in a `.env` file so you never have to
   retype it:
   - In the project folder, create a new file named exactly `.env`
     (there's already a `.env.example` you can copy and rename).
   - Open it and put your key in like this, with no quotes and no spaces
     around the `=`:
     ```
     GEMINI_API_KEY=your-actual-key-here
     ```
   - Save the file. That's it — the app automatically reads this file
     every time it starts, thanks to `python-dotenv`. You never need to
     type `export`/`set`/`$env:` again.
   - **Never commit this `.env` file to GitHub** — it has your private
     key in it. If you push this project to a public repo, add a line
     `.env` to a `.gitignore` file first so it doesn't get uploaded.

4. Run the app:
   ```bash
   streamlit run app.py
   ```

5. In the app, click **"Load a sample invoice"** to try it instantly
   with one of three included samples — one with a math error, one
   clean, one suspicious — or paste your own invoice text.

## Using a different AI provider (e.g. OpenAI)

If you'd rather use OpenAI instead, swap the `get_client()` and
`audit_invoice()` functions in `app.py` for the `openai` Python SDK —
the prompt (`SYSTEM_PROMPT`) stays exactly the same, only the API call
changes. This is worth mentioning in your pitch as a "provider-agnostic"
design choice.

## What broke and how I fixed it

*(Fill this in with your own experience once you've run it — the
buildathon brief specifically asks every track to document one real
failure case. For example: the model occasionally returned slightly
malformed JSON when instructions were phrased loosely. Fixed by using
Gemini's `response_mime_type="application/json"` config, which forces
strict JSON output every time.)*

## Possible extensions (mention these in your pitch even if unbuilt)

- Upload actual PDF/image receipts and OCR them first (e.g. with
  `pytesseract` or a multimodal model that reads images directly).
- Store audit history and show trends (e.g. "this vendor has had 3
  flagged invoices this month").
- Auto-generate a polite email back to the vendor asking for
  clarification on flagged items.
- Batch mode: upload 50 invoices at once and get a single summary
  report (this maps well to the "50+ record batch" language some
  buildathon tracks mention).
