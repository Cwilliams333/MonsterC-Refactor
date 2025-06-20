"""
Centralized logging configuration for MonsterC application.

This module provides:
- Structured logging to console and file with rotation
- @capture_exceptions decorator for service functions
- Context managers for logging service calls
- Production-ready configuration with multiple logging levels
"""

import functools
import logging
import logging.handlers
import os
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union
import json

# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured logs in JSON format for file logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value
        
        return json.dumps(log_entry, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """Console formatter with color coding for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format: [TIMESTAMP] LEVEL - MODULE.FUNCTION:LINE - MESSAGE
        formatted_message = (
            f"{color}[{datetime.fromtimestamp(record.created).strftime('%H:%M:%S')}] "
            f"{record.levelname:<8}{reset} - "
            f"{record.module}.{record.funcName}:{record.lineno} - "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted_message += f"\n{color}Exception: {record.exc_info[1]}{reset}"
        
        return formatted_message


class LoggingConfig:
    """Centralized logging configuration manager."""
    
    def __init__(
        self,
        app_name: str = "MonsterC",
        log_level: Union[str, int] = logging.INFO,
        log_dir: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_logging: bool = True,
        file_logging: bool = True,
        structured_file_logs: bool = True
    ):
        """
        Initialize logging configuration.
        
        Args:
            app_name: Application name for logger
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (defaults to ./logs)
            max_file_size: Maximum size of each log file in bytes
            backup_count: Number of backup log files to keep
            console_logging: Enable console logging
            file_logging: Enable file logging
            structured_file_logs: Use JSON format for file logs
        """
        self.app_name = app_name
        self.log_level = self._parse_log_level(log_level)
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_logging = console_logging
        self.file_logging = file_logging
        self.structured_file_logs = structured_file_logs
        
        # Create log directory if it doesn't exist
        if self.file_logging:
            self.log_dir.mkdir(exist_ok=True)
        
        self._configured = False
    
    def _parse_log_level(self, level: Union[str, int]) -> int:
        """Parse log level from string or int."""
        if isinstance(level, str):
            return getattr(logging, level.upper(), logging.INFO)
        return level
    
    def configure(self) -> logging.Logger:
        """
        Configure and return the main application logger.
        
        Returns:
            Configured logger instance
        """
        if self._configured:
            return logging.getLogger(self.app_name)
        
        # Get root logger and clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set root logger level
        root_logger.setLevel(self.log_level)
        
        # Configure console handler
        if self.console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_formatter = ColoredConsoleFormatter()
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Configure file handler with rotation
        if self.file_logging:
            log_file = self.log_dir / f"{self.app_name.lower()}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            
            if self.structured_file_logs:
                file_formatter = StructuredFormatter()
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
                )
            
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # Create application logger
        app_logger = logging.getLogger(self.app_name)
        
        self._configured = True
        return app_logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name."""
        if not self._configured:
            self.configure()
        return logging.getLogger(f"{self.app_name}.{name}")


# Global logging configuration instance
_logging_config = LoggingConfig()
logger = _logging_config.configure()


def configure_logging(
    app_name: str = "MonsterC",
    log_level: Union[str, int] = logging.INFO,
    log_dir: Optional[str] = None,
    **kwargs
) -> logging.Logger:
    """
    Configure application logging with the specified parameters.
    
    Args:
        app_name: Application name
        log_level: Minimum log level
        log_dir: Directory for log files
        **kwargs: Additional configuration options
    
    Returns:
        Configured logger instance
    """
    global _logging_config, logger
    _logging_config = LoggingConfig(
        app_name=app_name,
        log_level=log_level,
        log_dir=log_dir,
        **kwargs
    )
    logger = _logging_config.configure()
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module/component."""
    return _logging_config.get_logger(name)


class ServiceError(Exception):
    """Custom exception for service-level errors."""
    
    def __init__(self, message: str, user_message: str = None, details: Dict[str, Any] = None):
        """
        Initialize service error.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly error message
            details: Additional error details
        """
        super().__init__(message)
        self.user_message = user_message or "An error occurred while processing your request."
        self.details = details or {}


def capture_exceptions(
    user_message: str = None,
    log_level: int = logging.ERROR,
    reraise: bool = False,
    return_value: Any = None
) -> Callable[[F], F]:
    """
    Decorator that catches exceptions in service functions and logs them.
    
    Args:
        user_message: Custom user-friendly error message
        log_level: Log level for caught exceptions
        reraise: Whether to reraise the exception after logging
        return_value: Default return value when exception is caught
    
    Returns:
        Decorated function
    
    Example:
        @capture_exceptions(
            user_message="Failed to process CSV file",
            return_value=None
        )
        def process_csv(file_path: str) -> pd.DataFrame:
            # Function implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = get_logger(func.__module__)
            
            try:
                # Log function entry with parameters (at DEBUG level)
                func_logger.debug(
                    f"Entering {func.__name__}",
                    extra={
                        'function': func.__name__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                )
                
                result = func(*args, **kwargs)
                
                # Log successful completion
                func_logger.debug(
                    f"Successfully completed {func.__name__}",
                    extra={'function': func.__name__}
                )
                
                return result
                
            except ServiceError as e:
                # Handle our custom service errors
                func_logger.log(
                    log_level,
                    f"Service error in {func.__name__}: {e}",
                    extra={
                        'function': func.__name__,
                        'error_type': 'ServiceError',
                        'user_message': e.user_message,
                        'details': e.details
                    },
                    exc_info=True
                )
                
                if reraise:
                    raise
                return return_value
                
            except Exception as e:
                # Handle all other exceptions
                error_msg = user_message or f"Error in {func.__name__}: {str(e)}"
                
                func_logger.log(
                    log_level,
                    f"Unhandled exception in {func.__name__}: {e}",
                    extra={
                        'function': func.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'user_message': error_msg,
                        'traceback': traceback.format_exc()
                    },
                    exc_info=True
                )
                
                if reraise:
                    raise ServiceError(str(e), error_msg) from e
                
                return return_value
        
        return wrapper
    return decorator


@contextmanager
def log_service_call(
    service_name: str,
    operation: str,
    logger_name: str = None,
    log_level: int = logging.INFO,
    **context
):
    """
    Context manager for logging service calls with timing and context.
    
    Args:
        service_name: Name of the service being called
        operation: Description of the operation
        logger_name: Logger name (defaults to service_name)
        log_level: Log level for the call
        **context: Additional context to log
    
    Example:
        with log_service_call("CSVProcessor", "load_file", file_path=path):
            data = pd.read_csv(path)
    """
    call_logger = get_logger(logger_name or service_name)
    start_time = datetime.now()
    
    # Log start of operation
    call_logger.log(
        log_level,
        f"Starting {service_name}.{operation}",
        extra={
            'service': service_name,
            'operation': operation,
            'context': context,
            'start_time': start_time.isoformat()
        }
    )
    
    try:
        yield
        
        # Log successful completion
        duration = (datetime.now() - start_time).total_seconds()
        call_logger.log(
            log_level,
            f"Completed {service_name}.{operation} successfully",
            extra={
                'service': service_name,
                'operation': operation,
                'duration_seconds': duration,
                'status': 'success'
            }
        )
        
    except Exception as e:
        # Log failure
        duration = (datetime.now() - start_time).total_seconds()
        call_logger.error(
            f"Failed {service_name}.{operation}: {e}",
            extra={
                'service': service_name,
                'operation': operation,
                'duration_seconds': duration,
                'status': 'error',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        raise


def log_performance(threshold_seconds: float = 1.0) -> Callable[[F], F]:
    """
    Decorator to log performance warnings for slow functions.
    
    Args:
        threshold_seconds: Minimum execution time to trigger warning
    
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger = get_logger(f"performance.{func.__module__}")
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                if duration >= threshold_seconds:
                    perf_logger.warning(
                        f"Slow execution: {func.__name__} took {duration:.2f}s",
                        extra={
                            'function': func.__name__,
                            'duration_seconds': duration,
                            'threshold_seconds': threshold_seconds
                        }
                    )
                
                return result
                
            except Exception:
                duration = (datetime.now() - start_time).total_seconds()
                perf_logger.debug(
                    f"Function {func.__name__} failed after {duration:.2f}s",
                    extra={
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'status': 'error'
                    }
                )
                raise
        
        return wrapper
    return decorator


# Convenience functions for common logging patterns
def log_dataframe_info(df: 'pd.DataFrame', name: str, logger_name: str = None):
    """Log basic information about a pandas DataFrame."""
    info_logger = get_logger(logger_name or "data")
    info_logger.info(
        f"DataFrame {name} info",
        extra={
            'dataframe_name': name,
            'shape': df.shape,
            'columns': list(df.columns),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
            'null_counts': df.isnull().sum().to_dict()
        }
    )


def log_user_action(action: str, details: Dict[str, Any] = None, user_id: str = None):
    """Log user actions for analytics and debugging."""
    user_logger = get_logger("user_actions")
    user_logger.info(
        f"User action: {action}",
        extra={
            'action': action,
            'user_id': user_id,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    )


# Export main components
__all__ = [
    'configure_logging',
    'get_logger',
    'capture_exceptions',
    'log_service_call',
    'log_performance',
    'log_dataframe_info',
    'log_user_action',
    'ServiceError',
    'LoggingConfig'
]