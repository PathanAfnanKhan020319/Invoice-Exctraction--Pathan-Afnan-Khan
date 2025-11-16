"""
Parsing utilities for dates, amounts, and invoice numbers
"""

import re
from datetime import datetime, date
from typing import Optional, List
from dateutil import parser as date_parser
import logging

logger = logging.getLogger(__name__)


class DateParser: 
    """
    Parse dates from various string formats
    """
    
    # Common date formats
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ]
    
    @staticmethod
    def parse_date(date_string: str) -> Optional[date]:
        """
        Parse date from string using multiple formats
        
        Args:
            date_string: String containing a date
        
        Returns:
            date object if successful, None otherwise
        """
        if not date_string or not isinstance(date_string, str):
            return None
        
        date_string = date_string.strip()
        
        # Try dateutil parser first (most flexible)
        try:
            parsed_date = date_parser.parse(date_string, fuzzy=True)
            return parsed_date.date()
        except (ValueError, TypeError):
            pass
        
        # Try specific formats
        for fmt in DateParser.DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(date_string, fmt)
                return parsed_date.date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_string}")
        return None
    
    @staticmethod
    def extract_date_from_text(text: str) -> Optional[date]:
        """
        Extract date from free text
        
        Args:
            text: Text that may contain a date
        
        Returns:
            date object if found, None otherwise
        """
        if not text:
            return None
        
        # Common date patterns
        patterns = [
            r'\d{4}-\d{2}-\d{2}',  # 2024-03-15
            r'\d{1,2}/\d{1,2}/\d{4}',  # 3/15/2024 or 15/3/2024
            r'\d{1,2}-\d{1,2}-\d{4}',  # 3-15-2024
            r'[A-Z][a-z]+ \d{1,2},? \d{4}',  # March 15, 2024
            r'\d{1,2} [A-Z][a-z]+ \d{4}',  # 15 March 2024
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(0)
                parsed = DateParser.parse_date(date_str)
                if parsed:
                    return parsed
        
        return None


class AmountParser:
    """
    Parse monetary amounts from strings
    """
    
    @staticmethod
    def parse_amount(amount_string: str) -> Optional[float]:
        """
        Parse amount from string
        
        Args:
            amount_string: String containing a monetary amount
        
        Returns:
            float if successful, None otherwise
        """
        if not amount_string:
            return None
        
        if isinstance(amount_string, (int, float)):
            return float(amount_string)
        
        if not isinstance(amount_string, str):
            try:
                return float(amount_string)
            except (ValueError, TypeError):
                return None
        
        # Remove currency symbols and whitespace
        amount_string = amount_string.strip()
        amount_string = re.sub(r'[$€£¥₹]', '', amount_string)
        amount_string = amount_string.replace(' ', '')
        
        # Handle comma as thousand separator or decimal separator
        # If there's only one comma and it's followed by exactly 2 digits, it's decimal
        comma_count = amount_string.count(',')
        period_count = amount_string.count('.')
        
        if comma_count == 1 and period_count == 0:
            # Could be either 1,234 (thousand) or 1,23 (decimal)
            parts = amount_string.split(',')
            if len(parts[1]) == 2:
                # Likely decimal: 1,23 -> 1.23
                amount_string = amount_string.replace(',', '.')
            else:
                # Likely thousand: 1,234 -> 1234
                amount_string = amount_string.replace(',', '')
        elif comma_count > 1:
            # Multiple commas, they're thousand separators: 1,234,567
            amount_string = amount_string.replace(',', '')
        elif period_count > 1:
            # Multiple periods, they're thousand separators: 1.234.567,89
            amount_string = amount_string.replace('.', '', period_count - 1)
            amount_string = amount_string.replace(',', '.')
        
        # Try to convert to float
        try:
            return float(amount_string)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse amount: {amount_string}")
            return None
    
    @staticmethod
    def extract_amounts_from_text(text: str) -> List[float]:
        """
        Extract all monetary amounts from text
        
        Args:
            text: Text that may contain amounts
        
        Returns:
            List of floats
        """
        if not text:
            return []
        
        # Patterns for amounts
        patterns = [
            r'[$€£¥₹]\s*[\d,]+\.?\d{0,2}',  # $1,234.56
            r'[\d,]+\.\d{2}',  # 1,234.56
            r'\d+,\d{2}',  # European format 1234,56
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                parsed = AmountParser.parse_amount(match)
                if parsed is not None:
                    amounts.append(parsed)
        
        return amounts
    
    @staticmethod
    def find_total_amount(text: str) -> Optional[float]:
        """
        Find the total amount in text (usually the largest amount)
        
        Args:
            text: Text containing amounts
        
        Returns:
            float if found, None otherwise
        """
        # Look for keywords near amounts
        total_patterns = [
            r'(?:total|amount due|balance due|grand total|invoice total)[\s:]*[$€£¥₹]?\s*([\d,]+\.?\d{0,2})',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                parsed = AmountParser.parse_amount(amount_str)
                if parsed:
                    return parsed
        
        # Fallback: return the largest amount found
        amounts = AmountParser.extract_amounts_from_text(text)
        if amounts:
            return max(amounts)
        
        return None


class InvoiceNumberParser:
    """
    Parse invoice numbers from text
    """
    
    @staticmethod
    def extract_invoice_number(text: str) -> Optional[str]:
        """
        Extract invoice number from text
        
        Args:
            text: Text that may contain an invoice number
        
        Returns:
            Invoice number string if found, None otherwise
        """
        if not text:
            return None
        
        # Patterns for invoice numbers
        patterns = [
            r'(?:invoice|inv|bill|receipt)[\s#:]*([A-Z0-9\-]+)',
            r'\b(INV-\d+)\b',
            r'\b([A-Z]{2,4}-\d{4,})\b',
            r'(?:number|no|#)[\s:]*([A-Z0-9\-]+)',
            r'\b(\d{6,})\b',  # Pure numbers, 6+ digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_num = match.group(1).strip()
                # Validate it's not just a date or amount
                if len(invoice_num) >= 3 and not re.match(r'^\d{2}/\d{2}', invoice_num):
                    return invoice_num
        
        return None
    
    @staticmethod
    def normalize_invoice_number(invoice_number: str) -> str:
        """
        Normalize invoice number format
        
        Args:
            invoice_number: Raw invoice number
        
        Returns:
            Normalized invoice number
        """
        if not invoice_number:
            return ""
        
        # Remove extra whitespace
        invoice_number = ' '.join(invoice_number.split())
        
        # Convert to uppercase
        invoice_number = invoice_number.upper()
        
        return invoice_number