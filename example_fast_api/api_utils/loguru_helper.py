import functools
import json
import sys
from pathlib import Path
from typing import Union

def setup_logger(
    logger, config: Union[bool, dict] = False, config_file: str = "loguru_config.json"
) -> None:
    """
    Sets up a logger using Loguru. If a configuration file is provided,
    it tries to locate the file in the current directory or its subdirectories.
    If no configuration is found, it defaults to a standard logging setup.

    Args:
        logger : Logger object
        config (Union[bool, dict]): If `False`, use the default logging setup.
                                    If a dict, load the logging settings from
                                    a JSON config file.
        config_file (str): The name of the config file
                           (default: "log_config.json").

    Raises:
        FileNotFoundError: If the configuration file is not found and
        `config=True`.
    """

    # Create the log directory if it doesn't exist
    log_directory = Path("logs")
    log_directory.mkdir(exist_ok=True)

    # Remove the default logger to prevent duplicate logs
    logger.remove()

    if config:
        # Get the current directory of the running script or the CWD
        current_dir = (
            Path(sys.argv[0]).resolve().parent.parent
            if "ipykernel" not in sys.argv[0]
            else Path.cwd()
        )

        # Try to find the config file in the current directory or any subdir.
        config_file_path = next(current_dir.rglob(config_file), None)
        print(
            f"Current file path {current_dir}/n"
            f"Current file location {config_file_path}"
        )
        # If the configuration file is not found, revert to the default setup
        if not config_file_path:
            print("[WARNING] Cannot find logging config file," "using default setup.")
            return setup_logging(config=False)

        # Load the logging configuration from the config file
        with open(config_file_path, "r") as f:
            log_config = json.load(f)

        # Function to create a filter based on the specified log levels
        def make_level_filter(levels: list[str]) -> callable:
            def level_filter(record) -> bool:
                return record["level"].name in levels

            return level_filter

        # Iterate over the log configuration and add handlers
        for config in log_config:

            for level in config["levels"]:
                level = level.upper()
                if level not in logger._core.levels:
                    if "no" in config:
                        severity = config["no"]
                        logger.level(level, no=severity)
                    else:
                        print(
                            f"[WARNING]: Severity level 'no' not in "
                            f"{config['sink']}.\n"
                            f"[LEVEL] {level} was skipped and will NOT be "
                            f"callable."
                        )

            if config["sink"] == "sys.stdout":
                config["sink"] = sys.stdout
            else:
                # Construct the file path for the sink
                config["sink"] = log_directory / config["sink"]

            # Handle formatting with optional icon replacement
            icon = config.get("icon", "")
            fmt = config.get("format", "{time} {level} {message}")

            if "{icon}" in fmt:
                fmt = fmt.replace("{icon}", icon)

            # Common parameters for logger.add()
            add_params = {
                "sink": config["sink"],
                "filter": make_level_filter(config["levels"]),
                "level": 0,
                "format": fmt,
                "colorize": config.get("colorize", False),
            }

            # If the sink is a file path, include additional parameters
            if isinstance(config["sink"], str):
                file_params = {}

                # Match statement to include only non-empty file parameters
                for key in config:
                    match key:
                        case "rotation":
                            if config[key]:
                                file_params[key] = config[key]
                        case "retention":
                            if config[key]:
                                file_params[key] = config[key]
                        case "delay":
                            if config[key]:
                                file_params[key] = config[key]
                        case "encoding":
                            if config[key]:
                                file_params[key] = config[key]
                        case "mode":
                            if config[key]:
                                file_params[key] = config[key]
                        case "buffering":
                            if config[key]:
                                file_params[key] = config[key]
                add_params.update(file_params)

            # Add the logger with the parameters
            logger.add(**add_params)

        return logger

    # If no config or config is False, default logging setup is used
    print(
        "No configuration provided or config file not found. "
        "Initializing default logging setup."
    )

    # Define default log file paths
    error_log_file = log_directory.joinpath("error.log")
    info_log_file = log_directory.joinpath("info.log")
    debug_log_file = log_directory.joinpath("debug.log")

    # Log errors to 'error.log' and rotate when the log file reaches 1 MB
    logger.add(
        error_log_file,
        rotation="1 MB",
        level="ERROR",
        format="{time} {level} {message}",
    )

    # Log info and above to 'info.log' (INFO, WARNING, ERROR, CRITICAL)
    logger.add(
        info_log_file,
        rotation="1 MB",
        level="INFO",
        format="{time} {level} {message}",
    )

    # Log debug and above (everything) to 'debug.log'
    logger.add(
        debug_log_file,
        rotation="1 MB",
        level="DEBUG",
        format="{time} {level} {message}",
    )

    return logger