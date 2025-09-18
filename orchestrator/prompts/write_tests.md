# 🧪 Test Coverage Low

Current test count: {{test_count}}
Target: 15+ tests minimum

## Priority Tests to Add

### 1. API Endpoints
```python
def test_scan_endpoint_with_filters():
    """Test /api/v1/scan with various filter combinations"""
    response = client.get("/api/v1/scan?pattern=VCP&universe=sp500")
    assert response.status_code == 200
    assert "stocks" in response.json()

def test_analytics_empty_state():
    """Ensure analytics handles no data gracefully"""
    response = client.get("/api/v1/analytics/overview?run_id=999")
    assert response.status_code == 200
    assert response.json()["data_status"] in ["empty", "no_data"]
```

### 2. Chart Service
```python
def test_chart_metadata():
    """Verify chart endpoint returns proper metadata"""
    response = client.get("/api/v1/chart?symbol=AAPL")
    assert "chart_url" in response.json()
    assert "meta" in response.json()
```

### 3. Frontend Components
```javascript
// In __tests__/
test('PatternCard renders without crashing', () => {
  render(<PatternCard pattern="VCP" count={5} />);
});
```

Run tests:
```bash
python -m pytest -xvs
npm test
```
