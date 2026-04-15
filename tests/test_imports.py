"""Import-chain smoke test.

Verifies that every public module in the package can be imported without
a fatal DLL error, missing dependency, or broken __init__.  No models are
loaded and no I/O is performed.  If this test fails in CI it means the
install itself broke, not a logic regression.
"""


def test_config_importable():
    from photo_ai_workflow import config  # noqa: F401


def test_utils_importable():
    from photo_ai_workflow import utils  # noqa: F401


def test_logging_utils_importable():
    from photo_ai_workflow import logging_utils  # noqa: F401


def test_devices_importable():
    from photo_ai_workflow import devices  # noqa: F401


def test_pipeline_importable():
    # This import resolves all internal cross-imports including stage modules.
    from photo_ai_workflow import pipeline  # noqa: F401


def test_cli_importable():
    from photo_ai_workflow import cli  # noqa: F401
