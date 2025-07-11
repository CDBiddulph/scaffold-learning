import logging
import unittest
from scaffold_learning.core.logging_utils import suppress_all_except_root


class TestSuppressLogging(unittest.TestCase):

    def test_suppress_logging_context_manager(self):
        """Test logging suppression context manager"""
        # Create a handler to capture log messages
        captured_logs = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append(f"{record.name}:{record.levelname}:{record.getMessage()}")
        
        handler = TestHandler()
        handler.setLevel(logging.DEBUG)
        
        # Add handler to root logger to catch all messages
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
        
        try:
            # Create test loggers
            httpx_logger = logging.getLogger("httpx")
            
            # Clear any previous logs
            captured_logs.clear()
            
            # Test normal logging (should capture both)
            logging.info("Root message")
            httpx_logger.info("HTTPX message")
            self.assertEqual(len(captured_logs), 2)
            
            # Clear logs
            captured_logs.clear()
            
            # Test suppress_all_except_root (should only capture root)
            with suppress_all_except_root():
                logging.info("Root message")
                httpx_logger.info("HTTPX message")
            
            # Should only have root message
            self.assertEqual(len(captured_logs), 1)
            self.assertIn("root:INFO:Root message", captured_logs[0])
            
        finally:
            root_logger.removeHandler(handler)
