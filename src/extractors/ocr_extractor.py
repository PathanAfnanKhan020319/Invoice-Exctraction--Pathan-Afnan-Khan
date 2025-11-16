"""
OCR-based extraction using Tesseract and EasyOCR
"""

import os
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
import easyocr
import re
from typing import Dict, Any, Optional, List
import logging

from src.utils.parsers import DateParser, AmountParser, InvoiceNumberParser

from ..utils.validators import DataValidator

logger = logging.getLogger(__name__)


class OCRExtractor:
    """
    Extract invoice data using OCR
    """
    
    def __init__(self, engine: str = "easyocr", tesseract_path: str = None):
        """
        Initialize OCR extractor
        
        Args:
            engine: OCR engine to use ("tesseract", "easyocr", or "both")
            tesseract_path: Path to tesseract executable (if not in PATH)
        """
        self.engine = engine.lower()
        
        # Set tesseract path if provided
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Initialize EasyOCR if needed
        self.easyocr_reader = None
        if self.engine in ["easyocr", "both"]:
            try:
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize EasyOCR: {e}")
                if self.engine == "easyocr":
                    raise
        
        logger.info(f"OCR Extractor initialized with engine: {self.engine}")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to image file
        
        Returns:
            Extracted text
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Extract text based on engine
            if self.engine == "tesseract":
                text = self._extract_with_tesseract(processed_image)
            elif self.engine == "easyocr":
                text = self._extract_with_easyocr(processed_image)
            elif self.engine == "both":
                text1 = self._extract_with_tesseract(processed_image)
                text2 = self._extract_with_easyocr(processed_image)
                # Use the longer text (usually more complete)
                text = text1 if len(text1) > len(text2) else text2
            else:
                raise ValueError(f"Unknown OCR engine: {self.engine}")
            
            logger.info(f"Extracted {len(text)} characters from {image_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {e}")
            return ""
    
    def extract_text_from_pdf(self, pdf_path: str, poppler_path: str = None) -> str:
        """
        Extract text from PDF by converting to images
        
        Args:
            pdf_path: Path to PDF file
            poppler_path: Path to poppler binaries (if not in PATH)
        
        Returns:
            Extracted text from all pages
        """
        try:
            # Convert PDF to images
            if poppler_path:
                images = convert_from_path(pdf_path, poppler_path=poppler_path)
            else:
                images = convert_from_path(pdf_path)
            
            logger.info(f"Converted PDF to {len(images)} images")
            
            # Extract text from each page
            all_text = []
            for i, image in enumerate(images):
                # Convert PIL Image to numpy array
                image_np = np.array(image)
                
                # Preprocess
                processed = self._preprocess_image(image_np)
                
                # Extract text
                if self.engine == "tesseract":
                    text = self._extract_with_tesseract(processed)
                elif self.engine == "easyocr":
                    text = self._extract_with_easyocr(processed)
                else:  # both
                    text1 = self._extract_with_tesseract(processed)
                    text2 = self._extract_with_easyocr(processed)
                    text = text1 if len(text1) > len(text2) else text2
                
                all_text.append(text)
                logger.info(f"Extracted text from page {i+1}/{len(images)}")
            
            return "\n\n".join(all_text)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image: Input image as numpy array
        
        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Thresholding
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _extract_with_tesseract(self, image: np.ndarray) -> str:
        """Extract text using Tesseract"""
        try:
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Tesseract extraction error: {e}")
            return ""
    
    def _extract_with_easyocr(self, image: np.ndarray) -> str:
        """Extract text using EasyOCR"""
        try:
            if self.easyocr_reader is None:
                return ""
            
            results = self.easyocr_reader.readtext(image)
            text = "\n".join([result[1] for result in results])
            return text
        except Exception as e:
            logger.error(f"EasyOCR extraction error: {e}")
            return ""
    
    def extract_invoice_data(self, file_path: str) -> Dict[str, Any]:
        """
        Extract structured invoice data from file
        
        Args:
            file_path: Path to invoice file (PDF or image)
        
        Returns:
            Dictionary containing extracted invoice data
        """
        logger.info(f"Processing file: {file_path}")
        
        # Determine file type and extract text
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            text = self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        if not text or len(text) < 10:
            logger.warning(f"No text extracted from {file_path}")
            return {}
        
        # Extract structured data from text
        data = self._extract_fields_from_text(text)
        data['source_file'] = os.path.basename(file_path)
        data['extraction_method'] = 'ocr'
        
        # Add raw text for reference
        data['_raw_text'] = text
        
        logger.info(f"Extracted data from {file_path}: {list(data.keys())}")
        return data
    
    def _extract_fields_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract invoice fields from raw text
        
        Args:
            text: Raw OCR text
        
        Returns:
            Dictionary with extracted fields
        """
        data = {}
        
        # Extract invoice number
        invoice_num = InvoiceNumberParser.extract_invoice_number(text)
        if invoice_num:
            data['invoice_number'] = InvoiceNumberParser.normalize_invoice_number(invoice_num)
        
        # Extract date
        invoice_date = DateParser.extract_date_from_text(text)
        if invoice_date:
            data['invoice_date'] = invoice_date
        
        # Extract vendor name (look for patterns near top of text)
        vendor = self._extract_vendor_name(text)
        if vendor:
            data['vendor_name'] = DataValidator.normalize_vendor_name(vendor)
        
        # Extract total amount
        total = AmountParser.find_total_amount(text)
        if total:
            data['total_amount'] = total
        
        # Extract line items (basic extraction)
        line_items = self._extract_line_items(text)
        if line_items:
            data['line_items'] = line_items
        
        return data
    
    def _extract_vendor_name(self, text: str) -> Optional[str]:
        """
        Extract vendor name from text
        Usually appears near the top of the invoice
        """
        # Take first few lines
        lines = text.split('\n')[:10]
        
        # Look for company indicators
        for line in lines:
            line = line.strip()
            if len(line) > 3 and any(indicator in line.lower() for indicator in ['inc', 'llc', 'ltd', 'corp', 'company']):
                return line
        
        # Fallback: return first non-empty line
        for line in lines:
            line = line.strip()
            if len(line) > 3:
                return line
        
        return None
    
    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from text
        This is a basic implementation - LLM extraction is better for this
        """
        line_items = []
        
        # Look for table-like patterns
        # Pattern: description followed by quantity, unit price, total
        pattern = r'(.+?)\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})'
        
        matches = re.finditer(pattern, text)
        
        for i, match in enumerate(matches, 1):
            description = match.group(1).strip()
            quantity = float(match.group(2))
            unit_price = AmountParser.parse_amount(match.group(3))
            line_total = AmountParser.parse_amount(match.group(4))
            
            if unit_price is not None and line_total is not None:
                line_items.append({
                    'line_number': i,
                    'description': description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'line_total': line_total
                })
        
        return line_items