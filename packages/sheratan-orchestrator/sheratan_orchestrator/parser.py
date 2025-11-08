"""Parser module for processing different content types"""
import logging
from typing import Dict, Any, Optional
from html.parser import HTMLParser
import re

logger = logging.getLogger(__name__)


class TextExtractor(HTMLParser):
    """Extract text from HTML"""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
        self.in_style = False
    
    def handle_starttag(self, tag, attrs):
        if tag in ['script', 'style']:
            self.in_script = True
            self.in_style = True
    
    def handle_endtag(self, tag):
        if tag in ['script', 'style']:
            self.in_script = False
            self.in_style = False
    
    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            text = data.strip()
            if text:
                self.text_parts.append(text)
    
    def get_text(self) -> str:
        return ' '.join(self.text_parts)


class ContentParser:
    """Parser for different content types"""
    
    @staticmethod
    def parse(content: str, content_type: str = "text/plain") -> Dict[str, Any]:
        """
        Parse content based on type
        
        Args:
            content: Content to parse
            content_type: MIME type of content
            
        Returns:
            Dict with parsed content and metadata
        """
        logger.info(f"Parsing content type: {content_type}")
        
        # Determine parser based on content type
        if 'html' in content_type.lower():
            return ContentParser._parse_html(content)
        elif 'json' in content_type.lower():
            return ContentParser._parse_json(content)
        elif 'xml' in content_type.lower():
            return ContentParser._parse_xml(content)
        else:
            return ContentParser._parse_text(content)
    
    @staticmethod
    def _parse_html(content: str) -> Dict[str, Any]:
        """Parse HTML content"""
        try:
            extractor = TextExtractor()
            extractor.feed(content)
            text = extractor.get_text()
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return {
                "text": text,
                "format": "html",
                "success": True,
                "metadata": {
                    "original_length": len(content),
                    "extracted_length": len(text)
                }
            }
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return {
                "text": content,
                "format": "html",
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        """Parse JSON content"""
        try:
            import json
            data = json.loads(content)
            
            # Extract text from JSON
            text = ContentParser._extract_text_from_json(data)
            
            return {
                "text": text,
                "format": "json",
                "success": True,
                "data": data,
                "metadata": {
                    "original_length": len(content)
                }
            }
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return {
                "text": content,
                "format": "json",
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _parse_xml(content: str) -> Dict[str, Any]:
        """Parse XML content"""
        try:
            # Simple XML text extraction (remove tags)
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()
            
            return {
                "text": text,
                "format": "xml",
                "success": True,
                "metadata": {
                    "original_length": len(content),
                    "extracted_length": len(text)
                }
            }
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return {
                "text": content,
                "format": "xml",
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _parse_text(content: str) -> Dict[str, Any]:
        """Parse plain text content"""
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', content).strip()
        
        return {
            "text": text,
            "format": "text",
            "success": True,
            "metadata": {
                "length": len(text)
            }
        }
    
    @staticmethod
    def _extract_text_from_json(data: Any, max_depth: int = 5) -> str:
        """Recursively extract text from JSON structure"""
        if max_depth <= 0:
            return ""
        
        texts = []
        
        if isinstance(data, dict):
            for value in data.values():
                texts.append(ContentParser._extract_text_from_json(value, max_depth - 1))
        elif isinstance(data, list):
            for item in data:
                texts.append(ContentParser._extract_text_from_json(item, max_depth - 1))
        elif isinstance(data, str):
            texts.append(data)
        elif data is not None:
            texts.append(str(data))
        
        return ' '.join(filter(None, texts))
