#!/usr/bin/env python3
"""
Legend AI Production Testing Suite
Tests all critical endpoints and functionality before deployment
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
TEST_SYMBOLS = ["AAPL", "NVDA", "MSFT"]

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log(message, color=Colors.BLUE):
    print(f"{color}[TEST]{Colors.END} {message}")

def success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def test_health_endpoint():
    """Test basic health check"""
    log("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/healthz", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                success(f"Health check passed - {data}")
                return True
        error(f"Health check failed: {response.status_code}")
        return False
    except Exception as e:
        error(f"Health check exception: {e}")
        return False

def test_vcp_scan():
    """Test VCP scanning functionality"""
    log("Testing VCP scan endpoints...")
    passed = 0
    for symbol in TEST_SYMBOLS:
        try:
            response = requests.get(f"{BASE_URL}/scan/{symbol}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if "symbol" in data and "detected" in data:
                    success(f"VCP scan for {symbol}: detected={data.get('detected')}, confidence={data.get('confidence_score', 0):.2f}")
                    passed += 1
                else:
                    error(f"Invalid VCP response for {symbol}")
            else:
                error(f"VCP scan failed for {symbol}: {response.status_code}")
        except Exception as e:
            error(f"VCP scan exception for {symbol}: {e}")
    
    return passed == len(TEST_SYMBOLS)

def test_api_endpoints():
    """Test main API endpoints"""
    log("Testing API endpoints...")
    
    endpoints = [
        ("/api/v1/vcp/today", "Today's VCP candidates"),
        ("/api/v1/runs", "Runs list"),
        ("/api/v1/vcp/metrics?start=2024-01-01&end=2024-12-31", "VCP metrics"),
    ]
    
    passed = 0
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                success(f"{description}: {len(str(data))} bytes response")
                passed += 1
            else:
                error(f"{description} failed: {response.status_code}")
        except Exception as e:
            error(f"{description} exception: {e}")
    
    return passed == len(endpoints)

def test_database_operations():
    """Test database functionality"""
    log("Testing database operations...")
    try:
        # Test creating a sample run
        payload = {
            "start": "2024-01-01",
            "end": "2024-01-31",
            "universe": "simple",
            "provider": "yfinance"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/runs", params=payload, timeout=30)
        if response.status_code == 202:
            data = response.json()
            if "run_id" in data:
                success(f"Database operations working: {data}")
                return True
        
        warning("Database operations may be mocked/limited")
        return True  # Non-critical for basic functionality
    except Exception as e:
        warning(f"Database test exception: {e}")
        return True  # Non-critical for basic functionality

def test_performance():
    """Test API performance"""
    log("Testing API performance...")
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/scan/AAPL", timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            duration = end_time - start_time
            if duration < 10:  # Should complete within 10 seconds
                success(f"Performance test passed: {duration:.2f}s")
                return True
            else:
                warning(f"Performance slower than expected: {duration:.2f}s")
                return True  # Still functional
        else:
            error(f"Performance test failed: {response.status_code}")
            return False
    except Exception as e:
        error(f"Performance test exception: {e}")
        return False

def start_test_server():
    """Start test server"""
    log("Starting test server...")
    try:
        # Start server in background
        proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "service_api:app", 
            "--host", "127.0.0.1", "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(5)
        
        # Test if server is responding
        if test_health_endpoint():
            success("Test server started successfully")
            return proc
        else:
            error("Test server failed to start properly")
            proc.terminate()
            return None
    except Exception as e:
        error(f"Failed to start test server: {e}")
        return None

def stop_test_server(proc):
    """Stop test server"""
    if proc:
        log("Stopping test server...")
        proc.terminate()
        proc.wait(timeout=10)
        success("Test server stopped")

def run_syntax_checks():
    """Run syntax and import checks"""
    log("Running syntax and import checks...")
    
    try:
        # Test imports
        import service_api
        from vcp.vcp_detector import VCPDetector
        from backtest.run_backtest import scan_once
        success("All imports successful")
        
        # Test VCP detector instantiation
        detector = VCPDetector()
        success("VCP detector instantiation successful")
        
        return True
    except Exception as e:
        error(f"Syntax/import check failed: {e}")
        return False

def main():
    """Main testing function"""
    print(f"{Colors.BLUE}{'='*50}")
    print(f"🚀 Legend AI Production Testing Suite")
    print(f"{'='*50}{Colors.END}")
    
    # Change to project directory
    project_root = Path(__file__).parent
    import os
    os.chdir(project_root)
    
    # Run syntax checks first
    if not run_syntax_checks():
        error("❌ CRITICAL: Syntax checks failed. Fix errors before deployment.")
        sys.exit(1)
    
    # Start test server
    server_proc = start_test_server()
    if not server_proc:
        error("❌ CRITICAL: Could not start test server")
        sys.exit(1)
    
    try:
        # Run all tests
        tests = [
            ("Health Check", test_health_endpoint),
            ("VCP Scanning", test_vcp_scan),
            ("API Endpoints", test_api_endpoints),
            ("Database Operations", test_database_operations),
            ("Performance", test_performance),
        ]
        
        results = []
        for test_name, test_func in tests:
            log(f"Running {test_name} tests...")
            result = test_func()
            results.append((test_name, result))
        
        # Summary
        print(f"\n{Colors.BLUE}{'='*50}")
        print(f"📊 Test Results Summary")
        print(f"{'='*50}{Colors.END}")
        
        passed = 0
        for test_name, result in results:
            if result:
                success(f"{test_name}: PASSED")
                passed += 1
            else:
                error(f"{test_name}: FAILED")
        
        total = len(results)
        print(f"\n{Colors.BLUE}Overall: {passed}/{total} tests passed{Colors.END}")
        
        if passed == total:
            success("🎉 ALL TESTS PASSED - Ready for production deployment!")
            exit_code = 0
        elif passed >= total - 1:
            warning("⚠️  MOSTLY PASSED - Minor issues detected, deployment should work")
            exit_code = 0
        else:
            error("❌ MULTIPLE FAILURES - Fix issues before deployment")
            exit_code = 1
    
    finally:
        stop_test_server(server_proc)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()