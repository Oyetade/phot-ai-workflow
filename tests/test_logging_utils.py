"""Smoke tests for logging configuration — no side effects."""
import logging

import pytest
from photo_ai_workflow.logging_utils import configure_logging


class TestConfigureLogging:
    def test_default_level_is_info(self):
        configure_logging("INFO")
        assert logging.getLogger().level == logging.INFO

    def test_debug_level(self):
        configure_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_warning_level(self):
        configure_logging("WARNING")
        assert logging.getLogger().level == logging.WARNING

    def test_invalid_level_falls_back_to_info(self):
        # getattr on a non-existent attr on logging returns INFO (our fallback)
        configure_logging("NOTAREALLEVEL")
        assert logging.getLogger().level == logging.INFO
