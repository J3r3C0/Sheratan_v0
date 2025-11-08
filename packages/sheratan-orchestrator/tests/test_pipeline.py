"""Tests for ETL pipeline components"""
import pytest

from sheratan_orchestrator.crawler import Crawler
from sheratan_orchestrator.parser import ContentParser
from sheratan_orchestrator.chunker import TextChunker


@pytest.mark.asyncio
async def test_crawler_basic():
    """Test basic crawling functionality"""
    crawler = Crawler()
    
    try:
        # Note: This will fail in environments without internet
        # In real tests, you'd use mocking or a local test server
        result = await crawler.crawl("https://httpbin.org/html")
        
        assert "url" in result
        assert "content" in result
        assert "success" in result
    finally:
        await crawler.close()


def test_parser_html():
    """Test HTML parsing"""
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test paragraph.</p>
            <script>console.log('test');</script>
        </body>
    </html>
    """
    
    result = ContentParser.parse(html, "text/html")
    
    assert result["success"] is True
    assert result["format"] == "html"
    assert "Hello World" in result["text"]
    assert "test paragraph" in result["text"]
    # Script content should be filtered out
    assert "console.log" not in result["text"]


def test_parser_json():
    """Test JSON parsing"""
    json_str = '{"title": "Test Document", "content": "Sample content", "meta": {"author": "Test"}}'
    
    result = ContentParser.parse(json_str, "application/json")
    
    assert result["success"] is True
    assert result["format"] == "json"
    assert "Test Document" in result["text"]
    assert "Sample content" in result["text"]


def test_parser_text():
    """Test plain text parsing"""
    text = "This is a simple text document.\nWith multiple lines.\n\nAnd paragraphs."
    
    result = ContentParser.parse(text, "text/plain")
    
    assert result["success"] is True
    assert result["format"] == "text"
    assert "simple text document" in result["text"]


def test_chunker_basic():
    """Test basic text chunking"""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    
    text = "This is a test. " * 20  # Create text larger than chunk size
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 1
    assert all(c["length"] <= 50 + 10 for c in chunks)  # Allow some overflow
    assert all("index" in c for c in chunks)
    assert all("text" in c for c in chunks)


def test_chunker_with_separator():
    """Test chunking with paragraph separator"""
    chunker = TextChunker(chunk_size=100, chunk_overlap=10, separator="\n\n")
    
    text = "Paragraph 1 with some content.\n\nParagraph 2 with more content.\n\nParagraph 3 final content."
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    # Check that paragraphs are preserved when possible
    for chunk in chunks:
        assert "\n\n" in chunk["text"] or len(chunk["text"]) <= 100


def test_chunker_empty_text():
    """Test chunking with empty text"""
    chunker = TextChunker()
    
    chunks = chunker.chunk("")
    assert len(chunks) == 0
    
    chunks = chunker.chunk("   \n\n   ")
    assert len(chunks) == 0


def test_chunker_sentence_based():
    """Test sentence-based chunking"""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    
    text = "First sentence. Second sentence! Third sentence? Fourth sentence."
    
    chunks = chunker.chunk_by_sentences(text)
    
    assert len(chunks) > 0
    assert all("text" in c for c in chunks)
    assert all("index" in c for c in chunks)
