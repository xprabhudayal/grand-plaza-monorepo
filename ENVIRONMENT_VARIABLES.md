# Environment Variables Configuration

This document outlines the required and optional environment variables for the enhanced voice AI concierge system with RAG optimization and semantic intent detection.

## Core Application Variables

### Required Variables

```bash
# API Keys - Required for core functionality
GROQ_API_KEY=your_groq_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here

# OpenAI API Key - Required for enhanced evaluation framework
OPENAI_API_KEY=your_openai_api_key_here
```

### Optional Core Variables

```bash
# LangSmith Configuration
LANGSMITH_PROJECT=voice-ai-concierge
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_RUN_ENVIRONMENT=development

# API Configuration
API_BASE_URL=http://localhost:8000

# RAG Document Path
RAG_DOCUMENT_PATH=/path/to/menu-items.csv
```

## Enhanced Features Configuration

### Semantic Caching

```bash
# Enable/disable semantic caching (default: true)
CACHE_ENABLED=true

# Embedding model for cache similarity (default: all-MiniLM-L6-v2)
CACHE_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Cache directory (default: ./semantic_cache)
CACHE_DIR=./semantic_cache

# Cache settings
CACHE_SIMILARITY_THRESHOLD=0.95
CACHE_MAX_SIZE=1000
CACHE_TTL_HOURS=24
```

### Intent Classification

```bash
# Intent classification model (default: all-MiniLM-L6-v2)
INTENT_MODEL_PATH=all-MiniLM-L6-v2

# Intent classifier cache directory (default: ./intent_cache)
INTENT_CACHE_DIR=./intent_cache

# Intent confidence thresholds
INTENT_HIGH_CONFIDENCE_THRESHOLD=0.85
INTENT_MEDIUM_CONFIDENCE_THRESHOLD=0.70
INTENT_LOW_CONFIDENCE_THRESHOLD=0.55
```

### Query Processing & Reranking

```bash
# Query processor embedding model (default: all-MiniLM-L6-v2)
QUERY_PROCESSOR_MODEL=all-MiniLM-L6-v2

# Reranker model for result reranking (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
RERANKER_MODEL_PATH=cross-encoder/ms-marco-MiniLM-L-6-v2

# Enable/disable reranking (default: true)
RERANKING_ENABLED=true
```

### Enhanced Evaluation

```bash
# Evaluation model (separate from generation model to avoid bias)
EVALUATION_MODEL=gpt-4o-mini

# Generation model (used in RAG pipeline)
GENERATION_MODEL=qwen/qwen3-32b

# Evaluation results directory (default: ./evaluation_results)
EVALUATION_RESULTS_DIR=./evaluation_results

# RAGAS evaluation settings
RAGAS_ENABLED=true
```

## Performance & Optimization

```bash
# Model loading optimization
HF_HOME=/path/to/huggingface_cache
TRANSFORMERS_CACHE=/path/to/transformers_cache

# Performance monitoring
ENABLE_PERFORMANCE_LOGGING=true
LOG_LEVEL=INFO

# Memory optimization for large models
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

## Database & Storage

```bash
# ChromaDB persistence directory (default: ./chroma_db)
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Collection name for menu data (default: hotel_menu)
CHROMA_COLLECTION_NAME=hotel_menu
```

## Security & Production

```bash
# Production environment flag
ENVIRONMENT=production

# CORS settings
ALLOWED_ORIGINS=*
CORS_ENABLED=true

# Rate limiting
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60

# Security headers
SECURITY_HEADERS_ENABLED=true
```

## Model-Specific Configuration

### Sentence Transformers

```bash
# Default sentence transformer models used across the system
ST_EMBEDDING_MODEL=all-MiniLM-L6-v2
ST_CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Model download and caching
ST_MODEL_CACHE_DIR=./models/sentence_transformers
```

### Language Models

```bash
# Groq model configuration
GROQ_MODEL_NAME=qwen/qwen3-32b
GROQ_TEMPERATURE=0.1
GROQ_MAX_TOKENS=1000

# OpenAI model configuration (for evaluation)
OPENAI_MODEL_NAME=gpt-4o-mini
OPENAI_TEMPERATURE=0
OPENAI_MAX_TOKENS=1000
```

## Example .env File

```bash
# Core API Keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MISTRAL_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGSMITH_API_KEY=ls__xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# LangSmith Configuration
LANGSMITH_PROJECT=voice-ai-concierge
LANGSMITH_RUN_ENVIRONMENT=development

# Enhanced Features
CACHE_ENABLED=true
INTENT_MODEL_PATH=all-MiniLM-L6-v2
RERANKER_MODEL_PATH=cross-encoder/ms-marco-MiniLM-L-6-v2

# Performance
LOG_LEVEL=INFO
ENABLE_PERFORMANCE_LOGGING=true

# Document Path
RAG_DOCUMENT_PATH=/Users/prada/Desktop/coding/PYTHON/voice_ai_concierge/backend/RAG_DOCS/menu-items.csv
```

## Configuration Validation

You can validate your environment configuration by running:

```python
from backend.semantic_cache import get_semantic_cache
from backend.semantic_intent_classifier import get_intent_classifier
from backend.rag_pipeline import get_rag_pipeline

# Test cache
cache = get_semantic_cache()
print("Cache stats:", cache.get_cache_stats())

# Test intent classifier
classifier = get_intent_classifier()
test_result = classifier.classify_intent("I want to order pizza")
print("Intent classification test:", test_result)

# Test RAG pipeline
rag = get_rag_pipeline()
test_context = rag.get_context_for_query("What pizza options do you have?")
print("RAG test successful")
```

## Troubleshooting

### Common Issues

1. **Model Download Failures**
   - Ensure internet connection for first-time model downloads
   - Check HF_HOME and TRANSFORMERS_CACHE directories have write permissions
   - Verify sufficient disk space for model storage

2. **API Key Issues**
   - Ensure all required API keys are set correctly
   - Verify API key permissions and quotas
   - Check API key format (especially spaces or newlines)

3. **Memory Issues**
   - Adjust PYTORCH_CUDA_ALLOC_CONF for GPU memory management
   - Consider using smaller models if memory is limited
   - Monitor memory usage during evaluation runs

4. **Cache Issues**
   - Ensure cache directories have write permissions
   - Clear cache if experiencing corruption: remove cache directories
   - Check CACHE_ENABLED setting if caching isn't working

### Performance Tuning

- **For faster development**: Set smaller models and disable some features
- **For production**: Use optimized models and enable all caching features
- **For evaluation**: Ensure separate evaluation model to avoid bias

## Migration Notes

When upgrading from the previous version:

1. Install new dependencies from requirements.txt
2. Set the new environment variables
3. Clear old cache directories if format has changed
4. Run initial model downloads in a controlled environment
5. Test all components before full deployment

## Security Considerations

- Never commit API keys to version control
- Use environment-specific .env files
- Regularly rotate API keys
- Monitor API usage and costs
- Secure model cache directories in production