#!/usr/bin/env python3
"""
Logging utilities for scaffold execution.
"""

import logging
from contextlib import contextmanager


class RootLoggerOnlyFilter(logging.Filter):
    """Filter that only allows records from the root logger"""

    def filter(self, record):
        # Only allow root logger (used by logging.info/debug/etc calls)
        # Block all other loggers including httpcore, httpx, etc.
        return record.name == "root"


@contextmanager
def suppress_all_except_root():
    """Suppress all logging except from root logger (logging.info/debug calls)"""
    root_logger = logging.getLogger()
    filter_obj = RootLoggerOnlyFilter()

    # Add filter to root logger and all handlers
    handlers_with_filter = []
    root_logger.addFilter(filter_obj)
    handlers_with_filter.append((root_logger, None))

    for handler in root_logger.handlers:
        handler.addFilter(filter_obj)
        handlers_with_filter.append((None, handler))

    try:
        yield
    finally:
        # Remove filter from all places we added it
        for logger_ref, handler_ref in handlers_with_filter:
            if logger_ref is not None:
                logger_ref.removeFilter(filter_obj)
            else:
                handler_ref.removeFilter(filter_obj)
