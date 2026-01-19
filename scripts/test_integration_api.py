#!/usr/bin/env python3
"""
Integration tests for SlabHub API endpoints (Phases 2-4).

Tests the actual HTTP endpoints by running the FastAPI server.

Requirements:
- Server must be running on http://localhost:8000
- Database must have some test data

Usage:
    # Start server first:
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

    # Then run tests:
    python scripts/test_integration_api.py
"""

import sys
import requests
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 5


def test_health_endpoints():
    """Test health check endpoints."""
    print("\n[TEST] Health Endpoints")
    print("-" * 40)

    try:
        # Test main health endpoint
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "status" in data, "Missing 'status' field"
        assert "version" in data, "Missing 'version' field"
        print(f"  /health: OK (version {data.get('version')})")

        # Test database health
        r = requests.get(f"{BASE_URL}/health/db", timeout=TIMEOUT)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        print(f"  /health/db: OK")

        # Test storage health
        r = requests.get(f"{BASE_URL}/health/storage", timeout=TIMEOUT)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "storage_total_bytes" in data, "Missing storage info"
        print(f"  /health/storage: OK")

        print("  [PASS] Health endpoints working")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server - is it running?")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def test_export_csv():
    """Test CSV export endpoint."""
    print("\n[TEST] Export API - CSV")
    print("-" * 40)

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/export/slabs",
            params={"format": "csv"},
            timeout=TIMEOUT
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers["content-type"] == "text/csv; charset=utf-8", "Wrong content type"
        assert "attachment" in r.headers.get("content-disposition", ""), "Missing download header"

        # Check CSV content
        lines = r.text.split("\n")
        assert len(lines) > 0, "CSV is empty"
        header = lines[0]
        assert "SlabID" in header, "Missing SlabID column"
        assert "Name" in header, "Missing Name column"

        print(f"  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers['content-type']}")
        print(f"  Lines: {len(lines)}")
        print(f"  Headers: {header[:100]}...")
        print("  [PASS] CSV export working")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def test_export_json():
    """Test JSON export endpoint."""
    print("\n[TEST] Export API - JSON")
    print("-" * 40)

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/export/slabs",
            params={"format": "json"},
            timeout=TIMEOUT
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()

        assert "total" in data, "Missing 'total' field"
        assert "filters" in data, "Missing 'filters' field"
        assert "slabs" in data, "Missing 'slabs' field"
        assert isinstance(data["slabs"], list), "'slabs' should be a list"

        print(f"  Status: {r.status_code}")
        print(f"  Total slabs: {data['total']}")
        print(f"  Filters: {data['filters']}")
        print(f"  Sample count: {len(data['slabs'])}")
        print("  [PASS] JSON export working")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def test_export_with_filters():
    """Test export with filters."""
    print("\n[TEST] Export API - Filters")
    print("-" * 40)

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/export/slabs",
            params={
                "format": "json",
                "status": "available",
                "min_thickness": 1.0
            },
            timeout=TIMEOUT
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()

        print(f"  Status: {r.status_code}")
        print(f"  Total results: {data['total']}")
        print(f"  Applied filters: {data['filters']}")
        print("  [PASS] Filtered export working")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def test_export_invalid_format():
    """Test export with invalid format."""
    print("\n[TEST] Export API - Invalid Format")
    print("-" * 40)

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/export/slabs",
            params={"format": "xml"},
            timeout=TIMEOUT
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()

        assert "error" in data, "Should return error for unsupported format"
        assert "supported_formats" in data, "Should list supported formats"

        print(f"  Status: {r.status_code}")
        print(f"  Error: {data['error']}")
        print(f"  Supported: {data['supported_formats']}")
        print("  [PASS] Error handling working")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def test_import_csv_invalid():
    """Test import with invalid CSV (no file uploaded)."""
    print("\n[TEST] Import API - Invalid Request")
    print("-" * 40)

    try:
        # Try to post without file
        r = requests.post(
            f"{BASE_URL}/api/v1/import/metadata",
            timeout=TIMEOUT
        )
        # Should get 422 Unprocessable Entity for missing required field
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"

        print(f"  Status: {r.status_code}")
        print("  [PASS] Validation working")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def test_openapi_docs():
    """Test OpenAPI documentation endpoints."""
    print("\n[TEST] OpenAPI Documentation")
    print("-" * 40)

    try:
        # Test Swagger UI
        r = requests.get(f"{BASE_URL}/docs", timeout=TIMEOUT)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower(), "Not a Swagger UI page"
        print(f"  /docs: OK (Swagger UI)")

        # Test OpenAPI JSON
        r = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "openapi" in data, "Missing OpenAPI version"
        assert "info" in data, "Missing API info"
        assert "paths" in data, "Missing paths"

        # Check for our endpoints
        paths = data["paths"]
        assert "/api/v1/export/slabs" in paths, "Export endpoint not documented"
        assert "/api/v1/import/metadata" in paths, "Import endpoint not documented"

        print(f"  /openapi.json: OK")
        print(f"  Documented endpoints: {len(paths)}")
        print("  [PASS] OpenAPI docs available")
        return True

    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to server")
        return False
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 50)
    print("SlabHub API Integration Tests")
    print("=" * 50)
    print(f"\nServer: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")

    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Server is not running!")
        print("Please start the server first:")
        print("  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    results = []

    # Run tests
    results.append(("Health Endpoints", test_health_endpoints()))
    results.append(("Export CSV", test_export_csv()))
    results.append(("Export JSON", test_export_json()))
    results.append(("Export Filters", test_export_with_filters()))
    results.append(("Export Invalid Format", test_export_invalid_format()))
    results.append(("Import Validation", test_import_csv_invalid()))
    results.append(("OpenAPI Docs", test_openapi_docs()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = 0
    failed = 0

    for name, result in results:
        if result:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}")
            failed += 1

    print()
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
