"""
Main pipeline for invoice extraction and processing
"""

import os
import json
import yaml
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import joinedload

from .extractors import HybridExtractor
from .models import DatabaseManager
from .utils import DataValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvoiceExtractionPipeline:
    """
    End-to-end pipeline for invoice data extraction
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize pipeline with configuration"""

        self.config = self._load_config(config_path)

        self.extractor = HybridExtractor(
            ocr_engine=self.config['extraction']['ocr_engine'],
            llm_provider=self.config['extraction']['llm_provider'],
            llm_model=self.config['extraction']['llm_model'],
            confidence_threshold=self.config['extraction']['confidence_threshold'],
            max_retries=self.config['extraction']['max_retries']
        )

        self.db_manager = DatabaseManager(
            db_path=self.config['database']['path'],
            echo=self.config['database'].get('echo', False)
        )

        self._create_directories()

        logger.info("Invoice Extraction Pipeline initialized")

    # -------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            config = self._substitute_env_vars(config)
            logger.info(f"Configuration loaded from {config_path}")
            return config

        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._default_config()

    def _substitute_env_vars(self, config):
        """Replace ${ENV_VAR} in config"""

        def substitute(obj):
            if isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(i) for i in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                return os.getenv(obj[2:-1], obj)
            return obj

        return substitute(config)

    def _default_config(self):
        """Default fallback config"""
        return {
            'extraction': {
                'ocr_engine': 'easyocr',
                'llm_provider': 'openai',
                'llm_model': 'gpt-4-turbo-preview',
                'confidence_threshold': 0.7,
                'max_retries': 3
            },
            'database': {
                'path': 'outputs/invoices.db'
            },
            'output': {
                'save_json': True,
                'save_csv': True,
                'save_database': True,
                'json_path': 'outputs/extracted_data.json',
                'csv_path': 'outputs/extracted_data.csv'
            },
            'processing': {
                'parallel_workers': 4
            }
        }

    # -------------------------------------------------------------
    # FILE PROCESSING
    # -------------------------------------------------------------

    def _create_directories(self):
        """Create necessary directories."""
        for d in ["data/raw", "data/processed", "data/temp", "outputs", "logs"]:
            Path(d).mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: str, strategy="auto") -> Optional[Dict[str, Any]]:
        """Process a single file"""
        logger.info(f"Processing file: {file_path}")

        try:
            data = self.extractor.extract(file_path, strategy=strategy)

            if not data:
                logger.warning(f"No data extracted from {file_path}")
                return None

            # Validate invoice
            _, _ = DataValidator.validate_invoice_data(data)

            # Save to DB
            if self.config['output']['save_database']:
                self._save_to_database(data)

            logger.info(f"Successfully processed {file_path}")
            return data

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            return None

    def process_directory(self, directory: str, strategy="auto", parallel=True):
        """Process folder of invoices"""

        supported = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']
        files = []

        for ext in supported:
            files.extend(Path(directory).glob(f"**/*{ext}"))

        logger.info(f"Found {len(files)} invoice files")

        if not files:
            return []

        results = []

        if parallel and len(files) > 1:
            with ThreadPoolExecutor(max_workers=self.config['processing']['parallel_workers']) as ex:
                futures = {ex.submit(self.process_file, str(f), strategy): f for f in files}

                for fut in tqdm(as_completed(futures), total=len(files)):
                    try:
                        out = fut.result()
                        if out:
                            results.append(out)
                    except:
                        pass
        else:
            for f in tqdm(files):
                out = self.process_file(str(f), strategy)
                if out:
                    results.append(out)

        self._save_outputs(results)
        return results

    # -------------------------------------------------------------
    # DATABASE SAVE
    # -------------------------------------------------------------

    def _save_to_database(self, data: Dict[str, Any]):
        """Save invoice + line items to DB"""

        line_items = data.pop("line_items", [])

        allowed = [
            'invoice_number', 'vendor_name', 'invoice_date', 'due_date',
            'subtotal', 'tax_amount', 'total_amount', 'currency',
            'customer_name', 'payment_terms', 'notes',
            'source_file', 'extraction_method', 'confidence_score'
        ]

        invoice_data = {k: v for k, v in data.items() if k in allowed}

        try:
            self.db_manager.add_invoice(invoice_data, line_items)
            return True
        except Exception as e:
            logger.error(f"DB save failed: {e}")
            return False

    # -------------------------------------------------------------
    # OUTPUTS
    # -------------------------------------------------------------

    def _save_outputs(self, all_data):
        """Save JSON + CSV"""
        if not all_data:
            return

        # JSON
        if self.config['output'].get("save_json", True):
            with open(self.config['output']['json_path'], "w") as f:
                json.dump(all_data, f, indent=2, default=str)

        # CSV
        if self.config['output'].get("save_csv", True):
            flat = [{k: v for k, v in d.items() if k != "line_items"} for d in all_data]
            pd.DataFrame(flat).to_csv(self.config['output']['csv_path'], index=False)

    # -------------------------------------------------------------
    # QUERY FUNCTIONS
    # -------------------------------------------------------------

    def query_invoices(self, vendor=None, start_date=None, end_date=None):
        """Query DB"""
        if vendor:
            inv = self.db_manager.get_invoices_by_vendor(vendor, start_date, end_date)
        elif start_date and end_date:
            inv = self.db_manager.get_invoices_by_date_range(start_date, end_date)
        else:
            inv = self.db_manager.get_all_invoices()

        return pd.DataFrame([i.to_dict() for i in inv])

    def get_spending_by_vendor(self):
        return pd.DataFrame(self.db_manager.get_total_spend_by_vendor())

    def get_statistics(self):
        return self.db_manager.get_statistics()

    # -------------------------------------------------------------
    # FIXED: EXPORT ALL DATA (NO DETACHED INSTANCE ERROR)
    # -------------------------------------------------------------

    def export_all_data(self) -> pd.DataFrame:
        """Return all invoices with eager-loaded line items"""

        session = self.db_manager.get_session()

        try:
            invoices = (
                session.query(self.db_manager.Invoice)
                .options(joinedload(self.db_manager.Invoice.line_items))
                .all()
            )

            data = [inv.to_dict() for inv in invoices]
            return pd.DataFrame(data)

        finally:
            session.close()
