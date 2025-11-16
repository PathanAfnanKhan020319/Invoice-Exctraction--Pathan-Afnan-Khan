"""
Data validation utilities
"""

import re
from typing import Dict, Any, List, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validates extracted invoice data
    """
    
    @staticmethod
    def validate_invoice_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate invoice data
        
        Args:
            data: Dictionary containing invoice data
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ['invoice_number', 'vendor_name', 'invoice_date', 'total_amount']
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate invoice number
        if 'invoice_number' in data:
            if not DataValidator.validate_invoice_number(data['invoice_number']):
                errors.append(f"Invalid invoice number format: {data['invoice_number']}")
        
        # Validate vendor name
        if 'vendor_name' in data:
            if not isinstance(data['vendor_name'], str) or len(data['vendor_name'].strip()) == 0:
                errors.append("Vendor name must be a non-empty string")
        
        # Validate date
        if 'invoice_date' in data:
            if not isinstance(data['invoice_date'], date):
                errors.append(f"Invoice date must be a date object, got {type(data['invoice_date'])}")
        
        # Validate amount
        if 'total_amount' in data:
            if not DataValidator.validate_amount(data['total_amount']):
                errors.append(f"Invalid total amount: {data['total_amount']}")
        
        # Validate line items if present
        if 'line_items' in data and data['line_items']:
            for i, item in enumerate(data['line_items']):
                item_errors = DataValidator.validate_line_item(item)
                if item_errors:
                    errors.extend([f"Line item {i+1}: {err}" for err in item_errors])
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def validate_line_item(item: Dict[str, Any]) -> List[str]:
        """Validate a single line item"""
        errors = []
        
        required_fields = ['description', 'quantity', 'unit_price', 'line_total']
        for field in required_fields:
            if field not in item or item[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate numeric fields
        if 'quantity' in item:
            try:
                qty = float(item['quantity'])
                if qty <= 0:
                    errors.append("Quantity must be positive")
            except (ValueError, TypeError):
                errors.append(f"Invalid quantity: {item['quantity']}")
        
        if 'unit_price' in item:
            try:
                price = float(item['unit_price'])
                if price < 0:
                    errors.append("Unit price cannot be negative")
            except (ValueError, TypeError):
                errors.append(f"Invalid unit price: {item['unit_price']}")
        
        if 'line_total' in item:
            try:
                total = float(item['line_total'])
                if total < 0:
                    errors.append("Line total cannot be negative")
            except (ValueError, TypeError):
                errors.append(f"Invalid line total: {item['line_total']}")
        
        # Validate calculation if all fields present
        if all(f in item for f in ['quantity', 'unit_price', 'line_total']):
            try:
                expected_total = float(item['quantity']) * float(item['unit_price'])
                actual_total = float(item['line_total'])
                # Allow small rounding differences
                if abs(expected_total - actual_total) > 0.02:
                    logger.warning(f"Line total mismatch: expected {expected_total}, got {actual_total}")
            except (ValueError, TypeError):
                pass  # Already caught in individual validations
        
        return errors
    
    @staticmethod
    def validate_invoice_number(invoice_number: str) -> bool:
        """Validate invoice number format"""
        if not isinstance(invoice_number, str):
            return False
        
        invoice_number = invoice_number.strip()
        
        # Must not be empty
        if len(invoice_number) == 0:
            return False
        
        # Must be reasonable length
        if len(invoice_number) > 100:
            return False
        
        return True
    
    @staticmethod
    def validate_amount(amount: Any) -> bool:
        """Validate monetary amount"""
        try:
            amount_float = float(amount)
            # Must be non-negative and reasonable
            return 0 <= amount_float <= 1_000_000_000
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> bool:
        """Validate date range"""
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            return False
        return start_date <= end_date
    
    @staticmethod
    def clean_string(text: str) -> str:
        """Clean and normalize string data"""
        if not isinstance(text, str):
            return str(text)
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove control characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        return text.strip()
    
    @staticmethod
    def normalize_vendor_name(vendor_name: str) -> str:
        """Normalize vendor name for consistency"""
        if not isinstance(vendor_name, str):
            return str(vendor_name)
        
        # Clean the string
        vendor_name = DataValidator.clean_string(vendor_name)
        
        # Common abbreviations
        vendor_name = re.sub(r'\bInc\.?\b', 'Inc', vendor_name, flags=re.IGNORECASE)
        vendor_name = re.sub(r'\bLLC\.?\b', 'LLC', vendor_name, flags=re.IGNORECASE)
        vendor_name = re.sub(r'\bLtd\.?\b', 'Ltd', vendor_name, flags=re.IGNORECASE)
        vendor_name = re.sub(r'\bCorp\.?\b', 'Corp', vendor_name, flags=re.IGNORECASE)
        
        # Title case
        vendor_name = vendor_name.title()
        
        return vendor_name