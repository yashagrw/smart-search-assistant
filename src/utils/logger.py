import logging

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[37m',     # White
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'BLUE': '\033[34m',     # Blue
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Get the original formatted message
        log_message = super().format(record)
        
        # Add color based on log level
        if record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message

def configure_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger with the specified name and logging level.
    
    Args:
        name (str): The name of the logger.
        level (int): The logging level (default is INFO).
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)
        
        # Create colored formatter and add it to the handler
        formatter = ColoredFormatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        ch.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(ch)
    
    return logger