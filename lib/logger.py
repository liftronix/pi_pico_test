class Logger:
    """ Custom logger to enable/disable debug logs dynamically """
    DEBUG_MODE = True  # Set to False for production
    INFO_MODE = True  # Set to False for production
    WARN_MODE = True  # Set to False for production
    ERROR_MODE = True  # Set to False for production

    @staticmethod
    def debug(message):
        """ Print debug messages if debugging is enabled """
        if Logger.DEBUG_MODE:
            print(f"[DEBUG] {message}")

    @staticmethod
    def info(message):
        """ Print informational messages """
        if Logger.INFO_MODE:
            print(f"[INFO] {message}")

    @staticmethod
    def warn(message):
        """ Print warning messages """
        if Logger.WARN_MODE:
            print(f"[WARNING] {message}")

    @staticmethod
    def error(message):
        """ Print error messages """
        if Logger.ERROR_MODE:
            print(f"[ERROR] {message}")