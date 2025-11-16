"""
Hybrid extraction combining OCR and LLM for best accuracy
"""

import os
from typing import Dict, Any, Optional
import logging

from .ocr_extractor import OCRExtractor
from .llm_extractor import LLMExtractor
from ..utils.validators import DataValidator

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Combines OCR and LLM extraction for optimal results
    """
    
    def __init__(
        self,
        ocr_engine: str = "easyocr",
        llm_provider: str = "openai",
        llm_model: str = None,
        confidence_threshold: float = 0.7,
        max_retries: int = 3
    ):
        """
        Initialize hybrid extractor
        
        Args:
            ocr_engine: OCR engine to use
            llm_provider: LLM provider
            llm_model: LLM model name
            confidence_threshold: Minimum confidence for direct use
            max_retries: Maximum retry attempts
        """
        self.ocr_extractor = OCRExtractor(engine=ocr_engine)
        self.llm_extractor = LLMExtractor(provider=llm_provider, model=llm_model)
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        
        logger.info("Hybrid Extractor initialized")
    
    def extract(self, file_path: str, strategy: str = "auto") -> Dict[str, Any]:
        """
        Extract invoice data using hybrid approach
        
        Args:
            file_path: Path to invoice file
            strategy: Extraction strategy:
                - "auto": Try OCR first, use LLM if confidence low
                - "ocr_only": Use only OCR
                - "llm_only": Use only LLM
                - "both": Use both and merge results
        
        Returns:
            Dictionary containing extracted invoice data
        """
        logger.info(f"Extracting from {file_path} with strategy: {strategy}")
        
        if strategy == "ocr_only":
            return self._extract_ocr_only(file_path)
        elif strategy == "llm_only":
            return self._extract_llm_only(file_path)
        elif strategy == "both":
            return self._extract_both(file_path)
        else:  # auto
            return self._extract_auto(file_path)
    
    def _extract_ocr_only(self, file_path: str) -> Dict[str, Any]:
        """Extract using OCR only"""
        try:
            data = self.ocr_extractor.extract_invoice_data(file_path)
            data['extraction_method'] = 'ocr'
            return data
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {}
    
    def _extract_llm_only(self, file_path: str) -> Dict[str, Any]:
        """Extract using LLM only"""
        try:
            # First get text via OCR
            text = self._get_text_from_file(file_path)
            
            if not text:
                return {}
            
            # Extract using LLM
            data = self.llm_extractor.extract_from_text(text, os.path.basename(file_path))
            data['extraction_method'] = 'llm'
            return data
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {}
    
    def _extract_auto(self, file_path: str) -> Dict[str, Any]:
        """
        Auto strategy: Try OCR first, use LLM if confidence is low
        """
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                # Step 1: Try OCR extraction
                logger.info(f"Attempt {retry_count + 1}: Trying OCR extraction")
                ocr_data = self.ocr_extractor.extract_invoice_data(file_path)
                
                # Calculate confidence
                confidence = self._calculate_confidence(ocr_data)
                logger.info(f"OCR confidence: {confidence:.2f}")
                
                # If confidence is high enough, use OCR result
                if confidence >= self.confidence_threshold:
                    logger.info("OCR confidence acceptable, using OCR result")
                    ocr_data['confidence_score'] = confidence
                    ocr_data['extraction_method'] = 'ocr'
                    return ocr_data
                
                # Step 2: Low confidence, use LLM to improve
                logger.info("OCR confidence low, using LLM extraction")
                
                # Get raw text
                text = ocr_data.get('_raw_text', '')
                if not text:
                    text = self._get_text_from_file(file_path)
                
                # Extract with LLM
                llm_data, llm_confidence = self.llm_extractor.extract_with_confidence(
                    text, 
                    os.path.basename(file_path)
                )
                
                logger.info(f"LLM confidence: {llm_confidence:.2f}")
                
                # Merge results
                merged_data = self._merge_results(ocr_data, llm_data)
                merged_data['confidence_score'] = llm_confidence
                merged_data['extraction_method'] = 'hybrid'
                
                return merged_data
                
            except Exception as e:
                logger.error(f"Extraction attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                
                if retry_count >= self.max_retries:
                    logger.error("Max retries reached, returning empty result")
                    return {}
        
        return {}
    
    def _extract_both(self, file_path: str) -> Dict[str, Any]:
        """
        Extract using both methods and merge results
        """
        try:
            # Get OCR data
            ocr_data = self.ocr_extractor.extract_invoice_data(file_path)
            
            # Get text for LLM
            text = ocr_data.get('_raw_text', '')
            if not text:
                text = self._get_text_from_file(file_path)
            
            # Get LLM data
            llm_data = self.llm_extractor.extract_from_text(text, os.path.basename(file_path))
            
            # Merge results
            merged_data = self._merge_results(ocr_data, llm_data)
            merged_data['extraction_method'] = 'hybrid'
            
            # Calculate combined confidence
            ocr_conf = self._calculate_confidence(ocr_data)
            llm_conf = llm_data.get('confidence_score', 0.5)
            merged_data['confidence_score'] = (ocr_conf + llm_conf) / 2
            
            logger.info(f"Merged results with confidence: {merged_data['confidence_score']:.2f}")
            
            return merged_data
            
        except Exception as e:
            logger.error(f"Hybrid extraction failed: {e}")
            return {}
    
    def _get_text_from_file(self, file_path: str) -> str:
        """Get raw text from file using OCR"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf':
                return self.ocr_extractor.extract_text_from_pdf(file_path)
            else:
                return self.ocr_extractor.extract_text_from_image(file_path)
        except Exception as e:
            logger.error(f"Error getting text from file: {e}")
            return ""
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on data completeness
        
        Args:
            data: Extracted data dictionary
        
        Returns:
            Confidence score between 0 and 1
        """
        if not data:
            return 0.0
        
        # Required fields
        required_fields = ['invoice_number', 'vendor_name', 'invoice_date', 'total_amount']
        found_required = sum(1 for field in required_fields if field in data and data[field])
        
        base_confidence = found_required / len(required_fields)
        
        # Bonus for optional fields
        optional_fields = ['customer_name', 'due_date', 'subtotal', 'tax_amount']
        found_optional = sum(1 for field in optional_fields if field in data and data[field])
        
        optional_bonus = (found_optional / len(optional_fields)) * 0.2
        
        # Bonus for line items
        line_items_bonus = 0.1 if 'line_items' in data and data['line_items'] else 0.0
        
        total_confidence = min(1.0, base_confidence + optional_bonus + line_items_bonus)
        
        return total_confidence
    
    def _merge_results(self, ocr_data: Dict[str, Any], llm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge OCR and LLM results, preferring LLM for most fields
        
        Args:
            ocr_data: Data from OCR extraction
            llm_data: Data from LLM extraction
        
        Returns:
            Merged data dictionary
        """
        merged = {}
        
        # All possible fields
        all_fields = set(ocr_data.keys()) | set(llm_data.keys())
        
        # Remove internal fields
        all_fields.discard('_raw_text')
        all_fields.discard('extraction_method')
        all_fields.discard('confidence_score')
        
        for field in all_fields:
            ocr_value = ocr_data.get(field)
            llm_value = llm_data.get(field)
            
            # Prefer LLM for most fields (better at structure)
            if llm_value is not None:
                merged[field] = llm_value
            elif ocr_value is not None:
                merged[field] = ocr_value
        
        # Special handling for line items - prefer LLM
        if 'line_items' in llm_data and llm_data['line_items']:
            merged['line_items'] = llm_data['line_items']
        elif 'line_items' in ocr_data and ocr_data['line_items']:
            merged['line_items'] = ocr_data['line_items']
        
        # Validate merged data
        is_valid, errors = DataValidator.validate_invoice_data(merged)
        
        if not is_valid:
            logger.warning(f"Validation errors in merged data: {errors}")
        
        return merged