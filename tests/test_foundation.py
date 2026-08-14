"""Foundation tests to verify Phase 0 architecture boundaries and setup."""

import backend_ide
from backend_ide.infrastructure.logging import configure_logging, get_logger


def test_package_version():
    """Verify package imports and has correct version."""
    assert backend_ide.__version__ == "0.1.0"


def test_logging_configuration():
    """Verify structured logger initialization works without errors."""
    configure_logging("DEBUG")
    logger = get_logger("test_logger")
    assert logger is not None
    logger.info("Foundation test logging initialized", status="ok")
