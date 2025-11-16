"""
Test script to verify installation and setup
Run this after installation to check if everything is working
"""

import sys
import os
from pathlib import Path

print("="*60)
print("INVOICE EXTRACTION PIPELINE - SETUP TEST")
print("="*60)
print()

# Test 1: Python version
print("1. Checking Python version...")
if sys.version_info >= (3, 8):
    print(f"   ✓ Python {sys.version.split()[0]} (OK)")
else:
    print(f"   ✗ Python {sys.version.split()[0]} (Need 3.8+)")
print()

# Test 2: Required packages
print("2. Checking required packages...")
required_packages = [
    'pandas',
    'numpy',
    'pytesseract',
    'easyocr',
    'pdf2image',
    'PIL',
    'cv2',
    'openai',
    'anthropic',
    'sqlalchemy',
    'streamlit',
    'plotly',
    'yaml',
    'dateutil',
    'tqdm',
    'google.auth'
]

missing_packages = []
for package in required_packages:
    try:
        __import__(package)
        print(f"   ✓ {package}")
    except ImportError:
        print(f"   ✗ {package} (MISSING)")
        missing_packages.append(package)
print()

# Test 3: System dependencies
print("3. Checking system dependencies...")

# Tesseract
try:
    import pytesseract
    version = pytesseract.get_tesseract_version()
    print(f"   ✓ Tesseract OCR (v{version})")
except Exception as e:
    print(f"   ✗ Tesseract OCR (NOT FOUND)")
    print(f"      Install from: https://github.com/UB-Mannheim/tesseract/wiki")
print()

# Test 4: Environment variables
print("4. Checking environment variables...")
env_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_DRIVE_FOLDER_ID']

if os.path.exists('.env'):
    print("   ✓ .env file exists")
    from dotenv import load_dotenv
    load_dotenv()
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else value
            print(f"   ✓ {var} = {masked}")
        else:
            print(f"   ⚠ {var} (not set)")
else:
    print("   ⚠ .env file not found")
print()

# Test 5: Project structure
print("5. Checking project structure...")
required_dirs = [
    'data/raw',
    'data/processed',
    'data/temp',
    'outputs',
    'logs',
    'src',
    'src/extractors',
    'src/models',
    'src/utils',
    'notebooks'
]

for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✓ {dir_path}/")
    else:
        print(f"   ✗ {dir_path}/ (MISSING)")
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"      Created {dir_path}/")
print()

# Test 6: Import custom modules
print("6. Checking custom modules...")
sys.path.append(str(Path.cwd()))

try:
    from src.pipeline import InvoiceExtractionPipeline
    print("   ✓ src.pipeline")
except ImportError as e:
    print(f"   ✗ src.pipeline ({e})")

try:
    from src.extractors import OCRExtractor, LLMExtractor, HybridExtractor
    print("   ✓ src.extractors")
except ImportError as e:
    print(f"   ✗ src.extractors ({e})")

try:
    from src.models import DatabaseManager, Invoice, LineItem
    print("   ✓ src.models")
except ImportError as e:
    print(f"   ✗ src.models ({e})")

try:
    from src.utils import DataValidator, DateParser, AmountParser
    print("   ✓ src.utils")
except ImportError as e:
    print(f"   ✗ src.utils ({e})")
print()

# Test 7: Database creation
print("7. Testing database creation...")
try:
    from src.models import DatabaseManager
    db = DatabaseManager(db_path="outputs/test.db")
    print("   ✓ Database created successfully")
    
    # Clean up test database
    if os.path.exists("outputs/test.db"):
        os.remove("outputs/test.db")
        print("   ✓ Test database removed")
except Exception as e:
    print(f"   ✗ Database creation failed: {e}")
print()

# Test 8: Configuration
print("8. Checking configuration...")
if Path("config.yaml").exists():
    print("   ✓ config.yaml exists")
    try:
        import yaml
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        print("   ✓ config.yaml is valid")
    except Exception as e:
        print(f"   ✗ config.yaml error: {e}")
else:
    print("   ⚠ config.yaml not found (will use defaults)")
print()

# Summary
print("="*60)
print("SUMMARY")
print("="*60)

if missing_packages:
    print(f"⚠ Missing packages: {', '.join(missing_packages)}")
    print("  Install with: pip install -r requirements.txt")
else:
    print("✓ All packages installed")

print()
print("Next steps:")
print("1. Configure API keys in .env file")
print("2. Place sample invoices in data/raw/")
print("3. Run: jupyter notebook notebooks/02_extraction_pipeline.ipynb")
print("   OR: streamlit run streamlit_dashboard.py")
print()
print("For help, see README.md")
print("="*60)