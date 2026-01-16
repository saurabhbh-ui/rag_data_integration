# ETL Pipeline Test Suite

## Overview

This directory contains comprehensive unit and integration tests for the ETL pipeline.

## Quick Start

```bash
# Install test dependencies
pip install -r ../requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=ETL --cov-report=html
```

## Test Organization

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── test_models.py         # Base models (RAGEntry, ProcessingConfig, etc.)
│   ├── test_chunkers.py       # Chunker implementations
│   ├── test_parsers.py        # Parser implementations
│   └── test_reconstruction.py # Reconstruction agents
├── integration/               # Integration tests (future)
└── fixtures/                  # Shared test data and utilities
    ├── __init__.py
    └── test_data.py          # Mock data and helper functions
```

## Test Modules

### `test_models.py`
Tests for Pydantic models and configuration:
- RAGMetadata validation
- RAGEntry creation
- ProcessingConfig logic
- Enum definitions

### `test_chunkers.py`
Tests for document chunking:
- CharacterChunker
- RecursiveChunker
- MarkdownChunker
- ChunkerFactory

### `test_parsers.py`
Tests for file parsing:
- TextParser (.txt, .md)
- DocxParser (.docx)
- ExcelParser (.xlsx)
- ParserFactory

### `test_reconstruction.py`
Tests for chunk reconstruction/augmentation:
- NullReconstructionAgent
- SummaryAgent
- IterativeReconstructionAgent
- CombinedReconstructionAgent
- ReconstructionAgentFactory

## Test Fixtures

The `fixtures/` directory contains reusable test data:

```python
from tests.fixtures import (
    SAMPLE_TEXT_SHORT,
    SAMPLE_TEXT_MEDIUM,
    SAMPLE_TEXT_LONG,
    create_sample_config,
    create_sample_entry,
    create_mock_llm,
)
```

## Running Tests

### All Tests
```bash
pytest
```

### Specific Module
```bash
pytest tests/unit/test_chunkers.py
```

### Specific Test
```bash
pytest tests/unit/test_models.py::TestProcessingConfig::test_create_default_config
```

### With Coverage
```bash
pytest --cov=ETL --cov-report=html
open htmlcov/index.html
```

### Parallel Execution
```bash
pytest -n auto
```

## Test Markers

Tests are marked for easy filtering:

```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run tests requiring Azure
pytest -m requires_azure
```

## Writing Tests

### Template

```python
"""Tests for new feature."""

import pytest
from tests.fixtures import create_sample_data


class TestNewFeature:
    """Tests for new feature."""

    def test_basic_functionality(self):
        """Test basic use case."""
        # Arrange
        data = create_sample_data()
        
        # Act
        result = function_under_test(data)
        
        # Assert
        assert result == expected_value

    def test_error_handling(self):
        """Test error cases."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Best Practices

1. **Descriptive names:** `test_chunk_size_validation_rejects_negative_values`
2. **Single responsibility:** One concept per test
3. **AAA pattern:** Arrange, Act, Assert
4. **Use fixtures:** Avoid duplicating test data
5. **Mock external calls:** Don't rely on external services
6. **Test edge cases:** Empty inputs, None values, boundaries

## Coverage Goals

- **Unit Tests:** >90% coverage per module
- **Integration Tests:** Key workflows
- **Edge Cases:** Error handling, boundaries

## Current Coverage

Run to see current coverage:
```bash
pytest --cov=ETL --cov-report=term-missing
```

## Troubleshooting

### Import Errors
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
```

### Missing Dependencies
```bash
pip install -r ../requirements-test.txt
```

### Tests Fail Unexpectedly
```bash
# Run with verbose output
pytest -vv -s

# Stop on first failure
pytest -x
```

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure tests pass locally
3. Run full test suite
4. Check coverage doesn't decrease
5. Add to appropriate test file

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](../TESTING_GUIDE.md)
- [Code Validation Report](../CODE_VALIDATION_REPORT.md)

---

*For detailed testing instructions, see [TESTING_GUIDE.md](../TESTING_GUIDE.md)*
