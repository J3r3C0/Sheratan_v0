"""Seed data generators for demo and testing"""
import random
from typing import List, Dict, Any
from datetime import datetime


# Sample content templates
TECH_TOPICS = [
    "machine learning", "artificial intelligence", "data science",
    "cloud computing", "cybersecurity", "blockchain", "quantum computing",
    "internet of things", "edge computing", "microservices"
]

SAMPLE_PARAGRAPHS = [
    "In recent years, {topic} has become increasingly important in the technology industry. "
    "Organizations are investing heavily in {topic} to gain competitive advantages and improve efficiency.",
    
    "The field of {topic} continues to evolve rapidly, with new developments and innovations "
    "emerging regularly. Researchers and practitioners are exploring novel approaches to address "
    "complex challenges.",
    
    "Understanding {topic} requires a combination of theoretical knowledge and practical experience. "
    "Many companies are now offering specialized training programs to help professionals develop "
    "expertise in this area.",
    
    "The impact of {topic} extends across multiple industries, from healthcare and finance to "
    "manufacturing and retail. As adoption grows, we're seeing transformative changes in how "
    "businesses operate.",
    
    "Looking ahead, {topic} is expected to play an even more critical role in shaping the future "
    "of technology. Experts predict significant advancements over the next decade that will "
    "revolutionize the field."
]

COMPANY_NAMES = [
    "TechCorp", "InnovateCo", "DataSystems", "CloudFirst", "SecureNet",
    "BlockChain Inc", "QuantumLab", "IoT Solutions", "EdgeCompute", "MicroServe"
]

DOCUMENT_TYPES = ["whitepaper", "blog_post", "technical_guide", "case_study", "research_paper"]


def generate_tech_document(topic: str = None, doc_type: str = None) -> Dict[str, Any]:
    """
    Generate a sample technical document
    
    Args:
        topic: Technology topic (random if None)
        doc_type: Document type (random if None)
        
    Returns:
        Document dict with content, metadata, source
    """
    if topic is None:
        topic = random.choice(TECH_TOPICS)
    if doc_type is None:
        doc_type = random.choice(DOCUMENT_TYPES)
    
    # Generate content
    num_paragraphs = random.randint(3, 6)
    paragraphs = []
    for _ in range(num_paragraphs):
        template = random.choice(SAMPLE_PARAGRAPHS)
        paragraph = template.format(topic=topic)
        paragraphs.append(paragraph)
    
    content = "\n\n".join(paragraphs)
    
    # Generate metadata
    metadata = {
        "topic": topic,
        "type": doc_type,
        "author": f"{random.choice(['John', 'Jane', 'Alice', 'Bob'])} "
                 f"{random.choice(['Smith', 'Johnson', 'Williams', 'Brown'])}",
        "company": random.choice(COMPANY_NAMES),
        "word_count": len(content.split()),
        "created_date": datetime.utcnow().isoformat(),
        "tags": [topic, doc_type, random.choice(["tutorial", "overview", "advanced", "beginner"])]
    }
    
    # Generate source
    source = f"{doc_type}_{topic.replace(' ', '_')}_{random.randint(1000, 9999)}.txt"
    
    return {
        "content": content,
        "metadata": metadata,
        "source": source
    }


def generate_sample_dataset(
    size: str = "minimal",
    topics: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate a sample dataset of documents
    
    Args:
        size: Dataset size ('minimal', 'demo', 'full')
        topics: List of topics to use (random if None)
        
    Returns:
        List of document dicts
    """
    # Determine number of documents
    sizes = {
        "minimal": 5,
        "demo": 20,
        "full": 50
    }
    num_docs = sizes.get(size, 20)
    
    # Use provided topics or all topics
    available_topics = topics or TECH_TOPICS
    
    documents = []
    for i in range(num_docs):
        # Rotate through topics
        topic = available_topics[i % len(available_topics)]
        doc = generate_tech_document(topic=topic)
        documents.append(doc)
    
    return documents


def generate_user_query_examples() -> List[str]:
    """Generate example search queries for testing"""
    return [
        "What is machine learning?",
        "How does blockchain work?",
        "Cloud computing best practices",
        "Cybersecurity threats and mitigation",
        "Introduction to quantum computing",
        "IoT applications in healthcare",
        "Microservices architecture patterns",
        "Data science tools and frameworks",
        "Artificial intelligence ethics",
        "Edge computing use cases"
    ]


def generate_seed_file_content(size: str = "demo") -> str:
    """
    Generate seed file content in JSON format
    
    Args:
        size: Dataset size
        
    Returns:
        JSON string
    """
    import json
    documents = generate_sample_dataset(size=size)
    return json.dumps({"documents": documents}, indent=2)
