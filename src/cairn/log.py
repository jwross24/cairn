import contextlib
import json
import logging
import os
import sys

LOGGER_NAME = "cairn"
_logger = logging.getLogger(LOGGER_NAME)
_stderr_handler = None


class _StderrHandler(logging.Handler):
    def emit(self, record):
        with contextlib.suppress(ValueError):
            sys.stderr.write(self.format(record) + "\n")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "ts": round(record.created, 6),
            "level": record.levelname,
            "step": getattr(record, "step", None),
            "event": record.getMessage(),
        }
        data.update(getattr(record, "fields", {}) or {})
        return json.dumps(data, sort_keys=True, default=str)


def configure(level=None):
    global _stderr_handler
    name = (level or os.environ.get("CAIRN_LOG") or "INFO").upper()
    _logger.setLevel(getattr(logging, name, logging.INFO))
    if _stderr_handler is None:
        _stderr_handler = _StderrHandler()
        _stderr_handler.setFormatter(JsonFormatter())
        _logger.addHandler(_stderr_handler)
    return _logger.level


class StepLogger:
    def __init__(self, step):
        self.step = step

    def _emit(self, level, event, fields):
        _logger.log(level, event, extra={"step": self.step, "fields": fields})

    def debug(self, event, **fields):
        self._emit(logging.DEBUG, event, fields)

    def info(self, event, **fields):
        self._emit(logging.INFO, event, fields)

    def warning(self, event, **fields):
        self._emit(logging.WARNING, event, fields)


def get(step):
    return StepLogger(step)
