# Test Suite

## Running Tests

### Run all tests
```bash
# From project root
pytest

# Or with more verbose output
pytest -v
```

### Run specific test file
```bash
pytest tests/test_chunking.py
```

### Run specific test function
```bash
pytest tests/test_chunking.py::test_fixed_size_chunking_initialization
```

### Run tests by marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Result Storage

### Default Output
By default, pytest outputs test results to **stdout** (console). No files are created unless you specify output options.

### Generate JUnit XML Report
```bash
pytest --junitxml=tests/reports/junit.xml
```
Results stored in: `tests/reports/junit.xml`

### Generate HTML Report
First install pytest-html:
```bash
pip install pytest-html
```

Then run:
```bash
pytest --html=tests/reports/report.html --self-contained-html
```
Results stored in: `tests/reports/report.html`

### Generate Coverage Report
First install pytest-cov:
```bash
pip install pytest-cov
```

Then run:
```bash
pytest --cov=data_pipeline --cov=rag_core --cov-report=html:tests/reports/coverage
```
Results stored in: `tests/reports/coverage/index.html`

### Combined Report Generation
```bash
# Generate all reports at once
pytest \
    --junitxml=tests/reports/junit.xml \
    --html=tests/reports/report.html \
    --self-contained-html \
    --cov=data_pipeline \
    --cov=rag_core \
    --cov-report=html:tests/reports/coverage \
    --cov-report=term-missing
```

## Test Structure

- **Unit Tests**: Test individual functions/classes in isolation
  - `test_pdf_extraction.py`
  - `test_chunking.py`
  - `test_embeddings.py`
  - `test_vector_store.py`
  - `test_query_engine.py`

- **Integration Tests**: Test complete workflows
  - `test_rag_pipeline.py`
  - `test_fastapi_service.py`

## Test Data

Test data is stored in:
- **Temporary directories**: Created during test execution, cleaned up automatically
- **Fixtures**: Use `@pytest.fixture` for reusable test data
- **Mock data**: Some tests use mocks to avoid external dependencies

## Notes

- Tests can be run directly with `python tests/test_*.py` (path fix included)
- Recommended: Use `pytest` command for better test discovery and reporting
- Some tests require environment variables (e.g., `GROQ_API_KEY`) - see individual test files

