# Sheratan Embeddings

Local CPU-based embeddings with provider switching via environment variables.

## Features

- **Local Provider**: CPU-based embeddings using sentence-transformers (default)
- **OpenAI Provider**: OpenAI API embeddings (requires API key)
- **HuggingFace Provider**: HuggingFace Hub models

## Environment Variables

- `EMBEDDINGS_PROVIDER` - Provider to use (local, openai, huggingface). Default: local
- `EMBEDDINGS_MODEL` - Model name. Defaults depend on provider:
  - local: all-MiniLM-L6-v2
  - openai: text-embedding-ada-002
  - huggingface: sentence-transformers/all-MiniLM-L6-v2
- `OPENAI_API_KEY` - Required for OpenAI provider

## Usage

```python
from sheratan_embeddings.providers import get_embedding_provider

# Get provider based on ENV
provider = get_embedding_provider()

# Generate embeddings
texts = ["Hello world", "Another text"]
embeddings = provider.embed(texts)

# Generate single query embedding
query_embedding = provider.embed_query("search query")
```

## Installation

```bash
# Basic (local embeddings)
pip install -r requirements.txt

# For OpenAI
pip install openai

# For HuggingFace
pip install transformers
```
