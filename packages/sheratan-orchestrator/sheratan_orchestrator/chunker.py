"""Chunking module for splitting text into manageable pieces"""
import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class TextChunker:
    """Split text into chunks with overlap for better context preservation"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separator: str = "\n\n"
    ):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            separator: Preferred separator for splitting (paragraphs by default)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        logger.info(f"Chunking text of length {len(text)}")
        
        # Try to split by separator first (e.g., paragraphs)
        if self.separator in text:
            chunks = self._chunk_by_separator(text)
        else:
            # Fallback to character-based chunking
            chunks = self._chunk_by_chars(text)
        
        # Build result with metadata
        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_dict = {
                "text": chunk_text,
                "index": i,
                "length": len(chunk_text),
                "metadata": metadata or {}
            }
            result.append(chunk_dict)
        
        logger.info(f"Created {len(result)} chunks")
        return result
    
    def _chunk_by_separator(self, text: str) -> List[str]:
        """Chunk text using separator (smart chunking)"""
        # Split by separator
        parts = text.split(self.separator)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            part_size = len(part)
            
            # If single part exceeds chunk size, split it
            if part_size > self.chunk_size:
                # Finalize current chunk if exists
                if current_chunk:
                    chunks.append(self.separator.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split large part
                sub_chunks = self._chunk_by_chars(part)
                chunks.extend(sub_chunks)
                continue
            
            # If adding this part would exceed chunk size
            if current_size + part_size + len(self.separator) > self.chunk_size:
                if current_chunk:
                    chunks.append(self.separator.join(current_chunk))
                    
                    # Add overlap from previous chunk
                    overlap_text = current_chunk[-1] if current_chunk else ""
                    if len(overlap_text) <= self.chunk_overlap:
                        current_chunk = [overlap_text, part]
                        current_size = len(overlap_text) + part_size + len(self.separator)
                    else:
                        current_chunk = [part]
                        current_size = part_size
                else:
                    current_chunk = [part]
                    current_size = part_size
            else:
                current_chunk.append(part)
                current_size += part_size + len(self.separator)
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
        
        return chunks
    
    def _chunk_by_chars(self, text: str) -> List[str]:
        """Chunk text by characters (fallback method)"""
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # Try to break at a word boundary
            if end < text_len:
                # Look for space within last 10% of chunk
                search_start = max(start, end - self.chunk_size // 10)
                last_space = text.rfind(' ', search_start, end)
                
                if last_space > start:
                    end = last_space + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - self.chunk_overlap)
        
        return chunks
    
    def chunk_by_sentences(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by sentences (alternative method)
        
        Args:
            text: Text to chunk
            metadata: Optional metadata
            
        Returns:
            List of chunk dictionaries
        """
        # Split by sentence boundaries
        sentences = re.split(r'[.!?]+\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    
                    # Overlap: keep last sentence
                    if len(current_chunk[-1]) <= self.chunk_overlap:
                        current_chunk = [current_chunk[-1], sentence]
                        current_size = len(current_chunk[-1]) + sentence_size
                    else:
                        current_chunk = [sentence]
                        current_size = sentence_size
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add remaining
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # Build result
        result = []
        for i, chunk_text in enumerate(chunks):
            result.append({
                "text": chunk_text,
                "index": i,
                "length": len(chunk_text),
                "metadata": metadata or {}
            })
        
        logger.info(f"Created {len(result)} sentence-based chunks")
        return result
