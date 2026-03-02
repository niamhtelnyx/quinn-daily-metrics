# Bulletproof Context Overflow Protection

## Overview

This document describes the comprehensive safeguards implemented to prevent OpenAI API "Context overflow: prompt too large" errors in the AE Call Analysis system.

## Problem Statement

OpenAI's GPT-4o model has a 128k token context limit. When transcripts exceed this limit, the API returns a context overflow error, causing analysis failures. Some sales call transcripts can be very long (multi-hour calls), exceeding these limits.

## Solution Architecture

### 1. Pre-Flight Token Counting (`services/token_counter.py`)

**Accurate token counting BEFORE API calls:**

```python
from services import TokenCounter, count_tokens, check_fits_context

# Quick check
tokens = count_tokens("Your transcript here...", model='gpt-4o')

# Detailed check with limits
counter = TokenCounter('gpt-4o')
fits, details = counter.check_within_limits(transcript, system_prompt, output_tokens=4096)

if not fits:
    print(f"Overflow detected: {details['overflow_amount']:,} tokens over limit")
```

**Features:**
- Uses `tiktoken` for accurate OpenAI token counting (character estimation fallback)
- Knows limits for all major models (GPT-4o: 128k, GPT-4-turbo: 128k, Claude: 200k)
- Calculates safe limits accounting for system prompt, output tokens, and overhead

### 2. Smart Transcript Truncation (`services/transcript_processor.py`)

**Intelligent truncation strategies that preserve important content:**

```python
from services import TranscriptProcessor, TruncationStrategy

processor = TranscriptProcessor('gpt-4o')
result = processor.process_transcript(
    transcript,
    system_prompt,
    max_output_tokens=4096,
    strategy=TruncationStrategy.SMART_SECTIONS
)

print(f"Truncated: {result.was_truncated}")
print(f"Retention: {result.truncation_ratio:.1%}")
```

**Available Strategies:**

| Strategy | Description | Best For |
|----------|-------------|----------|
| `SMART_SECTIONS` | Keeps beginning (30%), end (30%), sampled middle (40%) | Most calls |
| `SPEAKER_AWARE` | Prioritizes speaker transitions and dialogue | Multi-party calls |
| `KEYWORD_PRESERVE` | Keeps sections with important keywords | Technical discussions |
| `SIMPLE` | Basic character truncation | Emergency fallback |

**Preserved Elements:**
- Call opening (introductions, context)
- Call closing (conclusions, next steps)
- Speaker transitions (key discussion points)
- Sections with keywords: budget, timeline, Quinn, integration, etc.

### 3. Enhanced OpenAI Client (`services/openai_client.py`)

**Bulletproof API client with automatic protection:**

```python
from services import OpenAIClient, create_robust_openai_client

# Create client with all protections enabled
client = create_robust_openai_client(enable_claude_fallback=True)

# Analyze any size transcript - protection is automatic
result = await client.analyze_call_transcript(
    huge_transcript,
    system_prompt,
    enable_fallback=True,  # Allow Claude fallback for very large
    truncation_strategy=TruncationStrategy.SMART_SECTIONS
)

# Check what happened
print(f"Provider: {result.provider}")
print(f"Truncated: {result.preprocessing_info['was_truncated']}")
print(f"Retention: {result.preprocessing_info['truncation_ratio']:.1%}")
```

**Protection Flow:**

```
1. Pre-flight token check
   ↓
2. If over limit → Apply truncation strategy
   ↓
3. Attempt OpenAI API call
   ↓
4. If context overflow error → Retry with more aggressive truncation
   ↓
5. If still fails + Claude available → Fallback to Claude (200k context)
   ↓
6. Track all metrics
```

### 4. Configuration (`config/settings.py`)

**New configuration options:**

```python
# OpenAI Config
OPENAI_CONTEXT_SAFETY_MARGIN=0.95  # Use 95% of available context
OPENAI_AUTO_TRUNCATE=true          # Auto-truncate large transcripts
OPENAI_ENABLE_FALLBACK=true        # Enable Claude fallback

# Token Limits Config
TOKEN_SAFETY_MARGIN=0.95
TOKEN_MIN_OUTPUT_RESERVE=2000
TOKEN_TRUNCATION_STRATEGY=smart_sections
TOKEN_ENABLE_CLAUDE_FALLBACK=true
TOKEN_LOG_USAGE=true
TOKEN_ALERT_THRESHOLD=0.85         # Warn at 85% usage
```

### 5. Error Handling (`services/error_handler.py`)

**Context overflow specific error handling:**

```python
# New error categories
ErrorCategory.CONTEXT_OVERFLOW     # Main overflow error
ErrorCategory.TRANSCRIPT_TOO_LARGE # Transcript exceeds all models
ErrorCategory.TRUNCATION_FAILED    # Truncation process failed

# Recovery strategies
- Automatic retry with more aggressive truncation
- Fallback to Claude (200k context)
- Graceful degradation to summary analysis
```

## Monitoring & Metrics

### Token Usage Tracking

```python
# Get client stats
stats = client.get_stats()
print(f"Total tokens used: {stats['total_tokens_used']:,}")
print(f"Overflows prevented: {stats['overflow_prevented_count']}")
print(f"Fallbacks used: {stats['fallback_count']}")

# Usage summary
summary = client.get_usage_summary()
print(f"Truncation rate: {summary['truncation_rate']:.1%}")
print(f"Avg retention: {summary['avg_truncation_retention']:.1%}")
```

### Logging

All context overflow events are logged with details:

```
WARNING - Token limit exceeded: 150,000 > 120,000 (overflow: 30,000)
INFO - Applying smart_sections truncation strategy
INFO - Truncation complete: 150,000 -> 100,000 tokens (66.7% retained)
INFO - ✅ Analysis completed - Input: 100,000, Output: 2,500
```

## Model Limits Reference

| Model | Context Limit | Safe Input | Max Output |
|-------|---------------|------------|------------|
| gpt-4o | 128,000 | 120,000 | 4,096 |
| gpt-4o-mini | 128,000 | 120,000 | 4,096 |
| gpt-4-turbo | 128,000 | 120,000 | 4,096 |
| gpt-4 | 8,192 | 6,000 | 1,024 |
| claude-3-sonnet | 200,000 | 180,000 | 4,096 |
| claude-3-opus | 200,000 | 180,000 | 4,096 |

## Testing

Run the test suite:

```bash
cd ae_call_analysis
python3 -m pytest tests/test_context_overflow_protection.py -v
```

Or manual validation:

```python
from services.token_counter import TokenCounter

counter = TokenCounter('gpt-4o')

# Test with your transcript
fits, details = counter.check_within_limits(
    your_transcript,
    "Your system prompt",
    output_tokens=4096
)

print(f"Fits: {fits}")
print(f"Details: {details}")
```

## Success Criteria

- ✅ Zero context overflow errors in production
- ✅ Automatic handling of large transcripts (>100k tokens)
- ✅ Fallback mechanisms working (Claude backup)
- ✅ Clear monitoring of token usage
- ✅ Cost-optimized model selection

## Files Changed

| File | Purpose |
|------|---------|
| `services/token_counter.py` | **NEW** - Accurate token counting with tiktoken |
| `services/transcript_processor.py` | **NEW** - Smart truncation strategies |
| `services/openai_client.py` | **ENHANCED** - Bulletproof API client |
| `services/error_handler.py` | **ENHANCED** - Context overflow recovery |
| `config/settings.py` | **ENHANCED** - Token limits configuration |
| `services/__init__.py` | **ENHANCED** - Export new modules |
| `tests/test_context_overflow_protection.py` | **NEW** - Comprehensive tests |
