#!/usr/bin/env python3
"""
Smoke test for SlabHub path system.

Quick validation that core path functionality works in the actual environment.
Run this after deployment to verify path system integrity.

Usage:
    python tests/smoke_test_paths.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_path_system():
    """Test basic path system functionality."""
    print("🧭 Testing SlabHub Path System...")

    try:
        # Import path system
        from backend.app.core.paths import get_path, resolve_path, LogicalPaths, generate_hash_filename, FileDetector, PathValidator, AtomicWriter, DiskMonitor
        print("✅ Path system imported successfully")

        # Test path construction
        data_path = get_path(LogicalPaths.DATA)
        print(f"✅ Data root: {data_path}")

        images_path = get_path(LogicalPaths.IMAGES)
        print(f"✅ Images path: {images_path}")

        qr_path = get_path(LogicalPaths.QR)
        print(f"✅ QR codes path: {qr_path}")

        # Test path resolution
        temp_file = resolve_path(LogicalPaths.TEMP, "test.txt")
        print(f"✅ Temp file path: {temp_file}")

        # Test hash filename generation
        test_file = Path(__file__)
        hash_name = generate_hash_filename(test_file)
        print(f"✅ Hash filename: {hash_name}")

        # Test directory creation
        test_dir = get_path("temp") / "smoke_test"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "test.txt"
        test_file.write_text("smoke test")
        print(f"✅ Created test file: {test_file}")

        # Test atomic write
        from backend.app.core.paths import AtomicWriter
        success = AtomicWriter.write_text_atomic(test_file, "atomic test")
        assert success
        content = test_file.read_text()
        assert content == "atomic test"
        print("✅ Atomic write works")

        # Test file validation
        from backend.app.core.paths import PathValidator
        exists = PathValidator.exists(test_file)
        assert exists
        print("✅ File validation works")

        # Test disk monitoring
        from backend.app.core.paths import DiskMonitor
        disk_stats = DiskMonitor.get_disk_usage(get_path(LogicalPaths.DATA))
        print(f"✅ Disk stats: {disk_stats}")

        # Test I/O latency
        latency = DiskMonitor.measure_io_latency(get_path(LogicalPaths.TEMP))
        print(f"✅ I/O latency: {latency:.3f}s")

        # Cleanup
        test_file.unlink()
        test_dir.rmdir()
        print("✅ Cleanup completed")

        print("\n🎉 All path system tests passed!")
        return True

    except Exception as e:
        print(f"❌ Path system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_path_validation():
    """Test path validation on startup."""
    print("\n🔍 Testing path validation...")

    try:
        # Import to trigger validation
        from backend.app.core.paths import FileDetector, LogicalPaths, get_path

        # Check that required directories exist
        required_paths = [
            LogicalPaths.DATA, LogicalPaths.IMAGES, LogicalPaths.QR, LogicalPaths.LOGS
        ]

        for logical in required_paths:
            path_obj = get_path(logical)
            if path_obj.exists():
                print(f"✅ {logical}: {path_obj}")
            else:
                print(f"⚠️  {logical}: {path_obj} (missing)")

        print("✅ Path validation completed")
        return True

    except Exception as e:
        print(f"❌ Path validation failed: {e}")
        return False

if __name__ == "__main__":
    success = True

    success &= test_path_system()
    success &= test_path_validation()

    if success:
        print("\n🚀 Path system smoke test PASSED")
        sys.exit(0)
    else:
        print("\n💥 Path system smoke test FAILED")
        sys.exit(1)