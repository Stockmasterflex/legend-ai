#!/usr/bin/env python3
"""
Integration test suite for Legend AI frontend-backend connection.
Tests all endpoints that the dashboard uses.
"""

import json
import sys
from typing import Dict, Tuple

import requests

# Configuration
API_BASE = "https://legend-api.onrender.com"
FRONTEND_BASE = "https://legend-ai-dashboard.vercel.app"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def test_endpoint(method: str, url: str, expected_status: int = 200, **kwargs) -> Tuple[bool, str, Dict]:
    """Test an endpoint and return results."""
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10, **kwargs)
        elif method == "POST":
            resp = requests.post(url, timeout=10, **kwargs)
        else:
            return False, f"Unsupported method: {method}", {}
        
        success = resp.status_code == expected_status
        
        try:
            data = resp.json()
        except:
            data = {"raw": resp.text[:200]}
        
        return success, f"Status: {resp.status_code}", data
    except requests.exceptions.Timeout:
        return False, "TIMEOUT", {}
    except Exception as e:
        return False, f"ERROR: {str(e)}", {}


def print_test(name: str, success: bool, message: str, data: Dict = None):
    """Pretty print test results."""
    status = f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
    print(f"{status} {name}: {message}")
    if not success and data:
        print(f"  {Colors.YELLOW}Response: {json.dumps(data, indent=2)[:200]}{Colors.END}")


def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Legend AI Integration Test Suite{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    print(f"{Colors.BLUE}[Backend Health]{Colors.END}")
    success, msg, data = test_endpoint("GET", f"{API_BASE}/healthz")
    print_test("Health check", success, msg, data)
    tests_passed += success
    tests_failed += not success
    
    # Test 2: Readiness check
    success, msg, data = test_endpoint("GET", f"{API_BASE}/readyz")
    print_test("Readiness check", success, msg, data)
    tests_passed += success
    tests_failed += not success
    
    # Test 3: Patterns API (what frontend uses)
    print(f"\n{Colors.BLUE}[Pattern API]{Colors.END}")
    success, msg, data = test_endpoint("GET", f"{API_BASE}/v1/patterns/all?limit=5")
    print_test("GET /v1/patterns/all", success, msg, data)
    if success and data.get("items"):
        print(f"  {Colors.GREEN}Found {len(data['items'])} patterns{Colors.END}")
    tests_passed += success
    tests_failed += not success
    
    # Test 4: Meta/status (frontend dashboard uses this)
    success, msg, data = test_endpoint("GET", f"{API_BASE}/v1/meta/status")
    print_test("GET /v1/meta/status", success, msg, data)
    if success:
        print(f"  Patterns: {data.get('rows_total', 0)}, Last scan: {data.get('last_scan_time', 'N/A')}")
    tests_passed += success
    tests_failed += not success
    
    # Test 5: Legacy endpoint (if frontend still uses it)
    success, msg, data = test_endpoint("GET", f"{API_BASE}/api/patterns/all")
    print_test("GET /api/patterns/all (legacy)", success, msg, data)
    tests_passed += success
    tests_failed += not success
    
    # Test 6: CORS check
    print(f"\n{Colors.BLUE}[CORS]{Colors.END}")
    headers = {"Origin": FRONTEND_BASE}
    success, msg, data = test_endpoint("GET", f"{API_BASE}/v1/patterns/all", headers=headers)
    print_test("CORS from Vercel origin", success, msg)
    tests_passed += success
    tests_failed += not success
    
    # Test 7: Frontend accessibility
    print(f"\n{Colors.BLUE}[Frontend]{Colors.END}")
    try:
        resp = requests.get(FRONTEND_BASE, timeout=10)
        success = resp.status_code == 200 and "Legend AI" in resp.text
        print_test("Frontend loads", success, f"Status: {resp.status_code}")
        tests_passed += success
        tests_failed += not success
    except Exception as e:
        print_test("Frontend loads", False, f"ERROR: {e}")
        tests_failed += 1
    
    # Test 8: Admin endpoints
    print(f"\n{Colors.BLUE}[Admin Endpoints]{Colors.END}")
    success, msg, data = test_endpoint("GET", f"{API_BASE}/admin/test-data?ticker=AAPL")
    print_test("GET /admin/test-data", success, msg)
    tests_passed += success
    tests_failed += not success
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    total = tests_passed + tests_failed
    pass_rate = (tests_passed / total * 100) if total > 0 else 0
    
    print(f"Tests Passed: {Colors.GREEN}{tests_passed}{Colors.END}/{total}")
    print(f"Tests Failed: {Colors.RED}{tests_failed}{Colors.END}/{total}")
    print(f"Pass Rate: {Colors.GREEN if pass_rate >= 80 else Colors.YELLOW}{pass_rate:.1f}%{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    # Frontend-Backend Connection Test
    print(f"{Colors.BLUE}[Frontend-Backend Connection]{Colors.END}")
    print("Testing if frontend can fetch data from backend...")
    
    # Simulate what the frontend would do
    try:
        resp = requests.get(
            f"{API_BASE}/v1/patterns/all",
            headers={
                "Origin": FRONTEND_BASE,
                "Accept": "application/json"
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"{Colors.GREEN}✓ Frontend can fetch patterns successfully!{Colors.END}")
            print(f"  Returned {len(data.get('items', []))} items")
        else:
            print(f"{Colors.RED}✗ Frontend fetch failed with status {resp.status_code}{Colors.END}")
            print(f"  Response: {resp.text[:200]}")
    except Exception as e:
        print(f"{Colors.RED}✗ Frontend fetch error: {e}{Colors.END}")
    
    print()
    
    # Exit with status
    sys.exit(0 if tests_failed == 0 else 1)


if __name__ == "__main__":
    main()

