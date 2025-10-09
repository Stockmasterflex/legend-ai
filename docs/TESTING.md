# Legend AI Testing Guide

## Overview

This guide covers testing strategies, how to run tests, how to add new test fixtures, and best practices for ensuring code quality.

## Test Structure

```
tests/
├── __pycache__/           # Python cache (gitignored)
├── api/                   # API endpoint tests
│   └── test_status.py
├── detectors/             # Pattern detector tests
│   └── test_vcp_fixtures.py
├── fixtures/              # Test data
│   ├── true_vcp.json     # Known VCP patterns
│   └── false_vcp.json    # Known non-VCP patterns
├── test_health.py         # Health endpoint tests
└── test_readyz_smoke.py   # Readiness tests
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/api/test_status.py -v

# Run tests in a directory
pytest tests/detectors/ -v

# Run with coverage report
pytest tests/ --cov=app --cov=vcp_ultimate_algorithm --cov-report=html

# Run only fast tests (skip integration tests)
pytest tests/ -m "not slow" -v

# Run with verbose output
pytest tests/ -vv --tb=short
```

### Configuration

**pytest.ini** (already configured):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

**Example**: VCP detector logic

```python
# tests/detectors/test_vcp_unit.py
def test_swing_point_detection():
    """Test swing high/low detection"""
    detector = VCPDetector()
    df = create_sample_data_with_swing_points()
    
    highs, lows = detector._find_swing_points(df)
    
    assert len(highs) >= 2
    assert len(lows) >= 2
```

### 2. Integration Tests

Test components working together.

**Example**: Full pattern detection pipeline

```python
# tests/detectors/test_vcp_fixtures.py
@pytest.mark.slow
def test_true_vcp_windows():
    """Test detector against known VCP patterns"""
    fixtures = load_fixture_set(Path("tests/fixtures/true_vcp.json"))
    det = VCPDetector(check_trend_template=False, min_price=30)
    
    hits = 0
    for f in fixtures:
        df = fetch_prices(f["symbol"])
        if df is None:
            continue
        sig = det.detect_vcp(df, symbol=f["symbol"])
        if sig.detected:
            hits += 1
    
    assert hits >= 1  # At least one should detect
```

### 3. API Tests

Test HTTP endpoints.

**Example**: Status endpoint

```python
# tests/api/test_status.py
def test_status_meta_shape():
    """GET /v1/meta/status returns expected fields"""
    from app.legend_ai_backend import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.get("/v1/meta/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "rows_total" in data
    assert "version" in data
```

### 4. Smoke Tests

Quick tests to verify basic functionality.

```python
# tests/test_readyz_smoke.py
def test_healthz_ok():
    """Verify /healthz endpoint responds"""
    from app.legend_ai_backend import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.get("/healthz")
    
    assert response.status_code == 200
    assert response.json()["ok"] is True
```

## Creating Test Fixtures

### What Are Fixtures?

Fixtures are known examples of patterns (both true positives and false positives) used to validate the detector.

### Finding Good Fixtures

1. **Manual Research**
   - Review historical charts on TradingView/FinViz
   - Look for obvious VCP patterns in 2023-2024
   - Examples: NVDA (Feb 2023), MSFT (Nov 2022), TSLA (Jan 2023)

2. **Criteria for True VCP**
   - Multiple tightening contractions
   - Volume drying up
   - Prior uptrend present
   - Clean pivot point
   - Eventually broke out with volume

3. **Criteria for False Positives**
   - Random consolidation (not VCP)
   - Base too deep (>35%)
   - No prior uptrend
   - Volume not drying up
   - Never broke out

### Adding New Fixtures

#### Step 1: Identify Pattern

```bash
# Check if ticker has data cached
ls data/price_history/NVDA.json

# If not, fetch it
python -c "
from app.data_fetcher import fetch_stock_data
df = fetch_stock_data('NVDA', days=365)
print(f'Fetched {len(df)} rows')
"
```

#### Step 2: Verify Pattern Manually

```python
# Quick test script
from vcp_ultimate_algorithm import VCPDetector
from app.data_fetcher import fetch_stock_data

df = fetch_stock_data('NVDA', days=365)
detector = VCPDetector(check_trend_template=False)
signal = detector.detect_vcp(df, 'NVDA')

print(f"Detected: {signal.detected}")
print(f"Confidence: {signal.confidence_score}")
print(f"Contractions: {len(signal.contractions) if signal.contractions else 0}")
```

#### Step 3: Add to Fixture File

**tests/fixtures/true_vcp.json**:
```json
[
  {
    "symbol": "NVDA",
    "date_range": "2023-01-01 to 2023-03-01",
    "description": "Clean 3-contraction VCP before breakout",
    "notes": "Strong volume dry-up, broke out above $250"
  },
  {
    "symbol": "MSFT",
    "date_range": "2022-11-01 to 2023-01-01",
    "description": "4-contraction VCP after October lows",
    "notes": "Tight final contraction, volume confirmation"
  }
]
```

**tests/fixtures/false_vcp.json**:
```json
[
  {
    "symbol": "SPY",
    "date_range": "2023-06-01 to 2023-08-01",
    "description": "Random consolidation, not VCP",
    "notes": "No contractions, sideways movement"
  }
]
```

#### Step 4: Run Tests

```bash
pytest tests/detectors/test_vcp_fixtures.py -v
```

## Test Data Management

### Price History Cache

Located in `data/price_history/`, these JSON files cache historical price data.

**Structure**:
```json
[
  {
    "date": "2023-01-03",
    "open": 123.45,
    "high": 125.67,
    "low": 122.34,
    "close": 124.56,
    "volume": 12345678
  }
]
```

**Refreshing cache**:
```bash
# Delete old cache
rm data/price_history/NVDA.json

# Re-fetch
python -c "
from app.data_fetcher import fetch_stock_data
df = fetch_stock_data('NVDA', days=365)
df.to_json('data/price_history/NVDA.json', orient='records', date_format='iso')
"
```

### Mock Data

For tests that don't need real data, use mock generator:

```python
from app.data_fetcher import _generate_mock_data

df = _generate_mock_data('TEST', days=180)
# Returns DataFrame with deterministic random walk
```

## Writing Good Tests

### Best Practices

1. **Arrange, Act, Assert (AAA)**
   ```python
   def test_vcp_confidence_score():
       # Arrange
       detector = VCPDetector()
       df = create_ideal_vcp_pattern()
       
       # Act
       signal = detector.detect_vcp(df, 'TEST')
       
       # Assert
       assert signal.detected is True
       assert signal.confidence_score >= 70
   ```

2. **One Assertion Per Test** (when possible)
   ```python
   def test_vcp_detected():
       signal = run_detection()
       assert signal.detected is True
   
   def test_vcp_has_contractions():
       signal = run_detection()
       assert len(signal.contractions) >= 2
   ```

3. **Descriptive Test Names**
   ```python
   # Good
   def test_vcp_detector_rejects_penny_stocks():
       pass
   
   # Bad
   def test_price_filter():
       pass
   ```

4. **Test Edge Cases**
   ```python
   def test_vcp_with_insufficient_data():
       """Detector should gracefully handle <60 days of data"""
       df = create_sample_data(days=30)
       signal = detector.detect_vcp(df, 'TEST')
       assert signal.detected is False
       assert 'Insufficient data' in signal.notes
   ```

### Test Fixtures (pytest)

Use pytest fixtures for reusable test data:

```python
import pytest

@pytest.fixture
def detector():
    """Provide VCP detector with production defaults"""
    return VCPDetector(
        min_price=30.0,
        min_volume=1_000_000,
        check_trend_template=True
    )

@pytest.fixture
def sample_vcp_data():
    """Provide clean VCP pattern data"""
    return create_ideal_vcp_pattern(
        contractions=3,
        base_depth=0.25,
        volume_dry_up=True
    )

def test_ideal_vcp_detected(detector, sample_vcp_data):
    """Test detector recognizes ideal VCP"""
    signal = detector.detect_vcp(sample_vcp_data, 'TEST')
    assert signal.detected is True
    assert signal.confidence_score >= 80
```

## Coverage Goals

### Current Coverage

Run coverage report:
```bash
pytest tests/ --cov=app --cov=vcp_ultimate_algorithm --cov-report=html
open htmlcov/index.html  # View in browser
```

### Target Coverage

- **Critical Paths**: 90%+ (detector, API endpoints)
- **Utility Functions**: 70%+
- **Overall**: 70%+

### What to Focus On

**High Priority**:
- VCP detection logic (`vcp_ultimate_algorithm.py`)
- API pattern endpoints (`app/legend_ai_backend.py`)
- Database queries (`app/db_queries.py`)

**Medium Priority**:
- Data fetchers (`app/data_fetcher.py`)
- Enrichment logic
- Scanner (`daily_market_scanner.py`)

**Low Priority** (acceptable gaps):
- Error handling edge cases
- Logging statements
- Admin/debug endpoints

## Continuous Integration

### GitHub Actions (Future)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Performance Testing

### Load Tests (Future)

Use `locust` or `k6` for API load testing:

**locustfile.py**:
```python
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_patterns(self):
        self.client.get("/v1/patterns/all?limit=100")
    
    @task(2)
    def get_status(self):
        self.client.get("/v1/meta/status")
```

Run:
```bash
locust -f locustfile.py --host https://legend-api.onrender.com
```

## Debugging Tests

### Verbose Output

```bash
# Print all logs
pytest tests/ -v --log-cli-level=DEBUG

# Show print statements
pytest tests/ -s

# Drop into debugger on failure
pytest tests/ --pdb

# Stop on first failure
pytest tests/ -x
```

### Debugging Fixtures

```python
def test_fixture_loading():
    """Debug test to inspect fixture structure"""
    fixtures = load_fixture_set(Path("tests/fixtures/true_vcp.json"))
    
    for f in fixtures:
        print(f"\nSymbol: {f['symbol']}")
        print(f"Date range: {f.get('date_range')}")
        print(f"Description: {f.get('description')}")
        
        df = fetch_prices(f['symbol'])
        if df is not None:
            print(f"Data rows: {len(df)}")
        else:
            print("No data cached")
```

## Common Issues

### Issue: Import Errors

```bash
ModuleNotFoundError: No module named 'app'
```

**Fix**: Ensure you're running from repo root, and `PYTHONPATH` includes current directory:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v
```

### Issue: Database Locked

```bash
sqlite3.OperationalError: database is locked
```

**Fix**: Close other processes using the database, or use test database:
```python
# conftest.py
import pytest
import os

@pytest.fixture(scope="session")
def test_db():
    os.environ["DATABASE_URL"] = "sqlite:///./test_legendai.db"
    yield
    os.remove("test_legendai.db")
```

### Issue: Slow Tests

```bash
pytest tests/ -v --duration=10  # Show 10 slowest tests
```

**Fix**: Mark slow tests and skip them during development:
```python
@pytest.mark.slow
def test_full_scan():
    # Takes minutes to run
    pass

# Run without slow tests
pytest tests/ -m "not slow"
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)

## Quick Reference

### Run Tests
```bash
pytest tests/ -v              # All tests
pytest tests/api/ -v          # API tests only
pytest -m "not slow"          # Skip slow tests
pytest --cov                  # With coverage
```

### Add Fixture
1. Find pattern in historical data
2. Add to `tests/fixtures/true_vcp.json`
3. Run `pytest tests/detectors/ -v`
4. Adjust detector if needed

### Debug Test
```bash
pytest tests/test_file.py::test_name -vv --pdb
```

### Check Coverage
```bash
pytest --cov=app --cov=vcp_ultimate_algorithm --cov-report=html
open htmlcov/index.html
```

