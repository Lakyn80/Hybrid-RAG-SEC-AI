import json
import logging
import sys


def build_log_payload(event: str, **fields) -> str:
    payload = {"event": str(event).strip()}
    payload.update({
        key: value
        for key, value in fields.items()
        if value is not None
    })
    return json.dumps(payload, ensure_ascii=False, default=str)


def log_structured(logger: logging.Logger, event: str, level: str = "info", **fields) -> None:
    log_method = getattr(logger, str(level).lower(), logger.info)
    log_method(build_log_payload(event, **fields))


def get_logger(name: str):

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
