# Intelligent Invoice Data Extraction & Modeling

**By Pathan Afnan Khan — AI Engineer | Data Scientist | Agentic AI Engineer**

An end-to-end AI document-processing pipeline that extracts structured invoice data from PDFs and images using OCR, LLM-assisted parsing, validation, normalization, and database storage.

[Portfolio](https://pathan-afnan-khan.vercel.app/) · [Projects](https://pathan-afnan-khan.vercel.app/projects) · [GitHub Profile](https://github.com/PathanAfnanKhan020319) · [LinkedIn](https://www.linkedin.com/in/afnan-khan4/)

## Core capabilities

- Multi-engine OCR with Tesseract and EasyOCR.
- LLM-assisted structured extraction using GPT / Claude.
- Hybrid OCR + LLM processing with confidence-based escalation.
- Structured extraction of invoice-level fields and line items.
- Validation and normalization of dates, amounts, vendors, and totals.
- SQLite storage for querying processed invoices.
- Streamlit dashboard for exploration and analytics.
- Batch processing and parallel execution support.

## Architecture

```text
PDF / Image
    ↓
OCR Extraction
    ↓
LLM Parsing
    ↓
Validation & Normalization
    ↓
Structured Invoice Data
    ↓
SQLite / Analytics Dashboard
```

## Extracted data

### Invoice-level fields

- Invoice number
- Vendor and customer name
- Invoice date and due date
- Subtotal, tax, and total amount
- Payment terms

### Line-item fields

- Description
- Quantity
- Unit price
- Line total
- Unit of measure
- Product code

## Tech stack

`Python` · `Tesseract` · `EasyOCR` · `OpenAI` · `Anthropic` · `Pandas` · `NumPy` · `SQLAlchemy` · `SQLite` · `Streamlit`

## Quick start

```bash
git clone https://github.com/PathanAfnanKhan020319/Invoice-Exctraction--Pathan-Afnan-Khan.git
cd Invoice-Exctraction--Pathan-Afnan-Khan
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Configure environment variables as needed:

```env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

Run the Streamlit interface:

```bash
streamlit run streamlit_dashboard.py
```

## Validation strategy

The pipeline uses multiple validation layers, including:

- Regex validation for invoice identifiers and amounts.
- Multi-format date parsing.
- Cross-field checks such as `quantity × unit price = line total`.
- Vendor-name normalization.
- Confidence thresholds for deciding when to escalate extraction to an LLM.

## Example pipeline usage

```python
from src.pipeline import InvoiceExtractionPipeline

pipeline = InvoiceExtractionPipeline()
results = pipeline.process_directory("data/raw")

spending = pipeline.get_spending_by_vendor()
print(spending)
```

## Current limitations

- Primarily designed around a single-currency workflow.
- Complex tables and handwritten documents may require stronger document-understanding models.
- Multi-page invoice splitting can be improved further.

## Potential extensions

- Multi-currency support.
- Layout-aware models such as LayoutLM-style or vision document models.
- Duplicate-invoice anomaly detection.
- REST API integration.
- Active-learning loops for extraction improvement.

## Portfolio

Explore more AI engineering, document intelligence, RAG, Agentic AI, and production AI projects:

**https://pathan-afnan-khan.vercel.app/projects**

---

**Pathan Afnan Khan**  
AI Engineer · Data Scientist · Agentic AI Engineer  
Portfolio: https://pathan-afnan-khan.vercel.app/
