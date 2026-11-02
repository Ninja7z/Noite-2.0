import logging

from noite.logging_setup import setup_logging


def test_setup_logging_writes_rotating_local_log_without_user_content(tmp_path):
    root_logger = logging.getLogger("noite")
    previous_handlers = set(root_logger.handlers)
    path = setup_logging(tmp_path)
    logger = logging.getLogger("noite.test")
    logger.info("Background operation failed (RuntimeError)")

    content = path.read_text(encoding="utf-8")

    assert path == tmp_path / "logs" / "noite.log"
    assert "Background operation failed (RuntimeError)" in content
    assert "user conversation" not in content
    for handler in set(root_logger.handlers) - previous_handlers:
        root_logger.removeHandler(handler)
        handler.close()
