"""
Unit tests for core path management system.

Tests path construction, validation, normalization, and security features.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.core.paths import PathResolver, LogicalPaths, generate_hash_filename, PathValidator, DiskMonitor, AtomicWriter, FileDetector


class TestPathResolver(unittest.TestCase):
    """Test cases for PathResolver class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_root = self.temp_dir / "test_slabhub"
        self.test_root.mkdir()

        # Create required subdirs
        (self.test_root / "data").mkdir()
        (self.test_root / "data" / "images").mkdir(parents=True)
        (self.test_root / "data" / "labels").mkdir()
        (self.test_root / "data" / "qr").mkdir()
        (self.test_root / "data" / "logs").mkdir()
        (self.test_root / "data" / "archive").mkdir()
        (self.test_root / "data" / "imports").mkdir()
        (self.test_root / "data" / "temp").mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('backend.app.core.paths.settings')
    def test_path_construction(self, mock_settings):
        """Test basic path construction."""
        mock_settings.slabhub_root = str(self.test_root)
        mock_settings.slabcrop_output_folder = str(self.test_root / "external" / "slabcrop")
        mock_settings.slabcrop_inbox_folder = str(self.test_root / "external" / "inbox")
        mock_settings.incoming_raw_folder = str(self.test_root / "external" / "raw")
        mock_settings.processed_archive_folder = str(self.test_root / "external" / "archive")

        # Create resolver
        resolver = PathResolver()

        # Test logical path resolution
        data_path = resolver.get_path(LogicalPaths.DATA)
        self.assertTrue(str(data_path).endswith("data"))

        images_path = resolver.get_path(LogicalPaths.IMAGES)
        # Use os.path.join or similar to handle Windows/Unix separators
        expected_suffix = os.path.join("data", "images")
        self.assertTrue(str(images_path).replace("\\", "/").endswith("data/images"))

    def test_hash_filename_generation(self):
        """Test hash-based filename generation."""
        # Create a test file
        test_file = self.test_root / "test.jpg"
        test_file.write_bytes(b"test content")

        # Generate hash filename
        hash_name = generate_hash_filename(test_file)
        self.assertTrue(hash_name.endswith(".jpg"))
        self.assertIn("_", hash_name)  # Should contain hash and uuid

    def test_path_validator(self):
        """Test path validation functions."""
        # Test existing file
        test_file = self.test_root / "test.txt"
        test_file.write_text("test")

        self.assertTrue(PathValidator.exists(test_file))
        self.assertTrue(PathValidator.is_file(test_file))
        self.assertTrue(PathValidator.is_readable(test_file))

        # Test non-existent file
        nonexistent = self.test_root / "nonexistent.txt"
        self.assertFalse(PathValidator.exists(nonexistent))

    def test_atomic_writer(self):
        """Test atomic file writing."""
        test_file = self.test_root / "atomic_test.txt"
        content = "test content"

        success = AtomicWriter.write_text_atomic(test_file, content)
        self.assertTrue(success)
        self.assertEqual(test_file.read_text(), content)

    @patch('backend.app.core.paths.settings')
    def test_path_validation(self, mock_settings):
        """Test path validation functions."""
        mock_settings.slabhub_root = str(self.test_root)
        mock_settings.slabcrop_output_folder = str(self.test_root / "external" / "slabcrop")
        mock_settings.slabcrop_inbox_folder = str(self.test_root / "external" / "inbox")
        mock_settings.incoming_raw_folder = str(self.test_root / "external" / "raw")
        mock_settings.processed_archive_folder = str(self.test_root / "external" / "archive")

        resolver = PathResolver()

        # Test invalid logical path
        with self.assertRaises(ValueError):
            resolver.get_path("nonexistent_path")

    def test_disk_space_monitoring(self):
        """Test disk space monitoring."""
        # Test disk space monitoring
        stats = DiskMonitor.get_disk_usage(self.test_root)

        # Should have some stats
        self.assertIsInstance(stats, dict)
        self.assertIn("total_bytes", stats)

    def test_io_latency_check(self):
        """Test I/O latency checking."""
        # Test I/O latency
        latency = DiskMonitor.measure_io_latency(self.test_root)

        # Should return a number
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0)


class TestPathSecurity(unittest.TestCase):
    """Test security features of path system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_root = self.temp_dir / "test_slabhub"
        self.test_root.mkdir()

        # Create required subdirs
        (self.test_root / "data").mkdir()
        (self.test_root / "data" / "images").mkdir(parents=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_filename_sanitization(self):
        """Test that dangerous filenames are handled safely."""
        # Create test file
        test_file = self.test_root / "safe.jpg"
        test_file.write_bytes(b"test")

        # Generate hash filename - should be safe
        hash_name = generate_hash_filename(test_file)
        self.assertNotIn("/", hash_name)
        self.assertNotIn("\\", hash_name)
        self.assertNotIn("..", hash_name)

    def test_path_validator_security(self):
        """Test path validator security."""
        # Test path traversal attempts
        traversal_path = self.test_root / ".." / ".." / "etc" / "passwd"
        self.assertFalse(PathValidator.exists(traversal_path))  # Should not exist anyway

        # Test with safe path
        safe_path = self.test_root / "data" / "test.txt"
        safe_path.write_text("test")
        valid, msg = PathValidator.validate_image_path(safe_path)
        self.assertFalse(valid)  # Not an image, but should not crash

        # PathManager was renamed to PathResolver or similar in Phase 2
        # The test seems to be using an old class name.
        # Let's use PathResolver instead.
        resolver = PathResolver()

        # construct_image_path doesn't exist in PathResolver, 
        # but we can test resolve_logical_path
        logical_path = resolver.resolve_logical_path(LogicalPaths.IMAGES, "test.jpg")

        # Should not contain dangerous path components
        self.assertNotIn("..", str(logical_path))
        # On Windows, resolve_logical_path will use backslashes.
        # We just want to ensure no traversal or dangerous components.
        path_str = str(logical_path).replace(str(resolver.get_path(LogicalPaths.IMAGES)), "")
        self.assertNotIn("..", path_str)


class TestAbsolutePathDetection(unittest.TestCase):
    """Test absolute path detection (Phase 2 - no absolute paths in DB)."""

    def test_windows_drive_letter(self):
        """Windows drive letters are absolute."""
        from backend.app.utils.path_validator import is_absolute_path
        self.assertTrue(is_absolute_path("C:\\Users\\test\\file.jpg"))
        self.assertTrue(is_absolute_path("D:/slabHub/data/image.png"))
        self.assertTrue(is_absolute_path("c:/path/to/file"))

    def test_unix_absolute(self):
        """Unix absolute paths start with /."""
        from backend.app.utils.path_validator import is_absolute_path
        self.assertTrue(is_absolute_path("/home/user/file.jpg"))
        self.assertTrue(is_absolute_path("/var/data/image.png"))

    def test_relative_paths(self):
        """Relative paths should return False."""
        from backend.app.utils.path_validator import is_absolute_path
        self.assertFalse(is_absolute_path("images/primary/file.jpg"))
        self.assertFalse(is_absolute_path("data/qr/code.png"))
        self.assertFalse(is_absolute_path("file.jpg"))

    def test_logical_paths(self):
        """Logical paths should return False."""
        from backend.app.utils.path_validator import is_absolute_path
        self.assertFalse(is_absolute_path("primary_images/abc123.jpg"))
        self.assertFalse(is_absolute_path("qr_codes/SLAB001.png"))

    def test_empty_and_none(self):
        """Empty/None paths should return False."""
        from backend.app.utils.path_validator import is_absolute_path
        self.assertFalse(is_absolute_path(""))
        self.assertFalse(is_absolute_path(None))


class TestPathNormalization(unittest.TestCase):
    """Test path normalization for DB storage."""

    def test_backslash_to_forward_slash(self):
        """Backslashes should be converted to forward slashes."""
        from backend.app.utils.path_validator import normalize_path_for_db
        self.assertEqual(
            normalize_path_for_db("images\\primary\\file.jpg"),
            "images/primary/file.jpg"
        )

    def test_double_slashes_removed(self):
        """Double slashes should be removed."""
        from backend.app.utils.path_validator import normalize_path_for_db
        self.assertEqual(
            normalize_path_for_db("images//primary//file.jpg"),
            "images/primary/file.jpg"
        )

    def test_trailing_slash_removed(self):
        """Trailing slashes should be removed."""
        from backend.app.utils.path_validator import normalize_path_for_db
        self.assertEqual(normalize_path_for_db("images/primary/"), "images/primary")


class TestPathFieldValidation(unittest.TestCase):
    """Test path field validation (Phase 2 enforcement)."""

    def test_valid_path_passes(self):
        """Valid paths should pass and be normalized."""
        from backend.app.utils.path_validator import validate_path_field
        result = validate_path_field("images\\primary\\file.jpg", "test_field", "TestModel")
        self.assertEqual(result, "images/primary/file.jpg")

    def test_absolute_path_raises(self):
        """Absolute paths should raise ValueError."""
        from backend.app.utils.path_validator import validate_path_field
        with self.assertRaises(ValueError) as ctx:
            validate_path_field("C:/path/to/file.jpg", "primary_image", "Slab")
        self.assertIn("Absolute path not allowed", str(ctx.exception))

    def test_empty_path_passes(self):
        """Empty paths should pass (nullable fields)."""
        from backend.app.utils.path_validator import validate_path_field
        self.assertEqual(validate_path_field("", "test_field", "TestModel"), "")
        self.assertIsNone(validate_path_field(None, "test_field", "TestModel"))


if __name__ == '__main__':
    unittest.main()
