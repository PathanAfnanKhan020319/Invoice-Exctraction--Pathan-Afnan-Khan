"""
LLM-based extraction using OpenAI GPT-4 or Anthropic Claude
"""

import os
import json
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from src.utils.parsers import DateParser, AmountParser, InvoiceNumberParser
from ..utils.validators import DataValidator

logger = logging.getLogger(__name__)


class LLMExtractor:
    """
    Extract invoice data using Large Language Models
    """

    def __init__(self, provider: str = "openai", model: str = None, api_key: str = None):
        self.provider = provider.lower()

        # -------------------------
        # OPENAI (NEW SDK FIXED)
        # -------------------------
        if self.provider == "openai":
            from openai import OpenAI
            import httpx

            # Disable any proxy injection
            http_client = httpx.Client(transport=httpx.HTTPTransport())


            self.client = OpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                http_client=http_client
            )

            self.model = model or "gpt-4o-mini"

        # -------------------------
        # ANTHROPIC (NEW SDK)
        # -------------------------
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
            self.model = model or "claude-3-sonnet-20240229"

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"LLM Extractor initialized with {self.provider} - {self.model}")


    # ---------------------------------------------------------
    # MAIN EXTRACT METHOD
    # ---------------------------------------------------------
    def extract_from_text(self, text: str, filename: str = None) -> Dict[str, Any]:
        if not text or len(text) < 10:
            logger.warning("Text too short for extraction")
            return {}

        try:
            prompt = self._create_extraction_prompt(text)

            if self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)

            data = self._parse_llm_response(response)

            data["source_file"] = filename or "unknown"
            data["extraction_method"] = f"llm_{self.provider}"

            return data

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {}


    # ---------------------------------------------------------
    # CALL OPENAI
    # ---------------------------------------------------------
    def _call_openai(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Return ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


    # ---------------------------------------------------------
    # CALL ANTHROPIC
    # ---------------------------------------------------------
    def _call_anthropic(self, prompt: str) -> str:
        try:
            result = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            return result.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


    # ---------------------------------------------------------
    # PROMPT
    # ---------------------------------------------------------
    def _create_extraction_prompt(self, text: str) -> str:
        return f"""Extract the following JSON fields from the invoice:

Required:
- invoice_number
- vendor_name
- invoice_date (YYYY-MM-DD)
- total_amount

Optional:
customer_name, due_date, subtotal, tax_amount, payment_terms, notes, line_items

Invoice text:
{text}

Return ONLY JSON.
"""


    # ---------------------------------------------------------
    # PARSE JSON
    # ---------------------------------------------------------
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            data = json.loads(response)
            return self._post_process_data(data)

        except Exception as e:
            logger.error("JSON parsing failed")
            logger.debug(f"Response: {response[:500]}")
            return {}


    # ---------------------------------------------------------
    # POST PROCESSING
    # ---------------------------------------------------------
    def _post_process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        processed = {}

        # Invoice number
        if data.get("invoice_number"):
            processed["invoice_number"] = str(data["invoice_number"])

        # Vendor name
        if data.get("vendor_name"):
            processed["vendor_name"] = DataValidator.normalize_vendor_name(data["vendor_name"])

        # Dates
        for field in ["invoice_date", "due_date"]:
            if data.get(field):
                dt = DateParser.parse_date(data[field])
                if dt:
                    processed[field] = dt

        # Amounts
        for field in ["total_amount", "subtotal", "tax_amount"]:
            if data.get(field) is not None:
                try:
                    processed[field] = float(data[field])
                except:
                    pass

        return processed
