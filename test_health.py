import requests
import json

def test_api_health():
    """Basic API health test"""
    try:
        response = requests.get('https://legend-api.onrender.com/healthz', timeout=10)
        assert response.status_code == 200
        print("✅ API health check passed")
        return True
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def test_signals_endpoint():
    """Test signals endpoint"""
    try:
        response = requests.get('https://legend-api.onrender.com/api/v1/signals?symbol=AAPL', timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Signals endpoint working - AAPL score: {data.get('signal', {}).get('score', 'N/A')}")
            return True
        else:
            print(f"❌ Signals endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Signals test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running backend tests...")
    test_api_health()
    test_signals_endpoint()
    print("Backend tests complete")
