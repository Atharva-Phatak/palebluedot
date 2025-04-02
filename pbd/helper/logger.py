import logging


def setup_logger(name: str, level=logging.INFO):
    """
    Set up and return a logger with console output

    Args:
        name (str): Logger name
        level (int): Logging level

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Create a handler to output logs to the console
        console_handler = logging.StreamHandler()
        # Define a basic formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        # Add the formatter to the handler
        console_handler.setFormatter(formatter)
        # Add the handler to the logger
        logger.addHandler(console_handler)

    return logger
