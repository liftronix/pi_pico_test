# logger.py

class Logger:
    """
    Flexible, colorful logger for MicroPython.
    Enables runtime control of log levels for development and production.
    """

    DEBUG_MODE = True
    INFO_MODE = True
    WARN_MODE = True
    ERROR_MODE = True

    # ANSI color codes
    _RESET = "\033[0m"
    _COLORS = {
        "DEBUG": "\033[90m",   # Gray
        "INFO":  "\033[94m",   # Blue
        "WARN":  "\033[93m",   # Yellow
        "ERROR": "\033[91m",   # Red
    }

    @staticmethod
    def debug(message):
        if Logger.DEBUG_MODE:
            print(f"{Logger._COLORS['DEBUG']}[DEBUG] {message}{Logger._RESET}")

    @staticmethod
    def info(message):
        if Logger.INFO_MODE:
            print(f"{Logger._COLORS['INFO']}[INFO] {message}{Logger._RESET}")

    @staticmethod
    def warn(message):
        if Logger.WARN_MODE:
            print(f"{Logger._COLORS['WARN']}[WARNING] {message}{Logger._RESET}")

    @staticmethod
    def error(message):
        if Logger.ERROR_MODE:
            print(f"{Logger._COLORS['ERROR']}[ERROR] {message}{Logger._RESET}")


# Export top-level convenience functions
debug = Logger.debug
info = Logger.info
warn = Logger.warn
error = Logger.error
