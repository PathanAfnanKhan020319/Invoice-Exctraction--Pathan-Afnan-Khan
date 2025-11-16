# Quick Start Guide

Get up and running with the Invoice Extraction Pipeline in 10 minutes!

## 🚀 Installation (5 minutes)

### Step 1: Clone and Setup Environment

```bash
# Navigate to your project directory
cd invoice-extraction

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Install System Dependencies

**For Windows:**

1. Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
2. Download Poppler: https://github.com/oschwartz10612/poppler-windows/releases
3. Add both to your PATH

**For Mac:**

```bash
brew install tesseract poppler
```

**For Linux:**

```bash
sudo apt-get install tesseract-ocr poppler-utils
```

### Step 3: Configure API Keys

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get API keys from:

* OpenAI: https://platform.openai.com/api-keys
* Anthropic: https://console.anthropic.com/

### Step 4: Test Your Setup

```bash
python test_setup.py
```

This will verify all installations and create necessary directories.

## 📄 Processing Your First Invoice (3 minutes)

### Option 1: Using Python Script (Easiest)

```bash
# Place your invoices in data/raw/
# Then run:
python run_pipeline.py data/raw --strategy auto
```

### Option 2: Using Interactive Dashboard

```bash
streamlit run streamlit_dashboard.py
```

Then:

1. Click on "Upload & Process" in the sidebar
2. Upload your invoice files
3. Click "Process Invoices"
4. View results in the Dashboard

### Option 3: Using Jupyter Notebook

```bash
jupyter notebook notebooks/02_extraction_pipeline.ipynb
```

Follow the cells step by step.

## 📊 Quick Commands

```bash
# Process all invoices in a directory
python run_pipeline.py data/raw

# Use different strategy
python run_pipeline.py data/raw --strategy llm_only

# Enable parallel processing (faster)
python run_pipeline.py data/raw --parallel

# Run dashboard
streamlit run streamlit_dashboard.py

# Test setup
python test_setup.py
```

## 🔍 Quick Python Examples

### Process a Single File

```python
from src.pipeline import InvoiceExtractionPipeline

pipeline = InvoiceExtractionPipeline()
data = pipeline.process_file("data/raw/invoice.pdf")
print(data)
```

### Query All Invoices

```python
from src.pipeline import InvoiceExtractionPipeline

pipeline = InvoiceExtractionPipeline()
df = pipeline.export_all_data()
print(df)
```

### Get Spending by Vendor

```python
from src.pipeline import InvoiceExtractionPipeline

pipeline = InvoiceExtractionPipeline()
spending = pipeline.get_spending_by_vendor()
print(spending)
```

## 🎯 Sample Data

Don't have invoices? Use these sample sources:

1. **Download Sample Invoices:**
   * https://www.docparser.com/sample-invoices/
   * https://templates.invoicehome.com/invoice-template-us-neat-750px.png
2. **Create Test Invoice:**
   ```bash
   # Download a sample
   curl -o data/raw/sample.png https://templates.invoicehome.com/invoice-template-us-neat-750px.png
   ```

## 📝 Configuration Options

Edit `config.yaml` to customize:

```yaml
extraction:
  ocr_engine: "easyocr"           # or "tesseract", "both"
  llm_provider: "openai"          # or "anthropic"
  llm_model: "gpt-4-turbo-preview"
  confidence_threshold: 0.7
  
processing:
  parallel_workers: 4
  
database:
  path: "outputs/invoices.db"
```

## 🐛 Troubleshooting

### "Tesseract not found"

* Make sure Tesseract is installed and in your PATH
* Or set the path in `.env`: `TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe`

### "No module named 'src'"

* Make sure you're in the project root directory
* The `src` folder should be in the current directory

### "API key not found"

* Check your `.env` file exists in the project root
* Make sure API keys are properly set
* Try: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"`

### "No invoices found"

* Check that files are in `data/raw/`
* Verify file formats: PDF, PNG, JPG, JPEG, TIFF
* Check file extensions are lowercase

### "PDF extraction failed"

* Make sure Poppler is installed
* On Windows, set `POPPLER_PATH` in `.env`

## 📚 Next Steps

1. ✅ **Read the full README.md** for detailed documentation
2. ✅ **Explore the Jupyter notebooks** for advanced usage
3. ✅ **Try the Streamlit dashboard** for interactive analysis
4. ✅ **Customize the extractors** for your specific invoice formats
5. ✅ **Add validation rules** in `src/utils/validators.py`

## 💡 Tips

* Start with `strategy="auto"` - it's the smartest option
* Use `--parallel` for processing many files faster
* Check `confidence_score` in results - lower scores may need review
* The hybrid approach (OCR + LLM) gives best results but costs more
* Use `ocr_only` for simple, well-formatted invoices to save on API costs

## 🆘 Getting Help

* Check `README.md` for detailed information
* Run `python test_setup.py` to verify your installation
* Look at example notebooks in `notebooks/`
* Check logs in `logs/pipeline.log`

## 🎉 You're Ready!

Start processing invoices and extracting valuable data!

```bash
python run_pipeline.py data/raw --strategy auto --parallel
```

Happy extracting! 📊
