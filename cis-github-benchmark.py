import argparse
from github import Github
import logging
import sys
from datetime import datetime
import platform

# GLOBALS
ARGS = {}
LOGGER = logging.getLogger()
FILE_DELIMITER = "/"
if platform.system() == "Windows":
    FILE_DELIMITER = "\\"

def parseArgs():
    parser = argparse.ArgumentParser(
        prog="cis-github-benchmark",
        description="A CIS benchmark audit tool for GitHub environments, because it somehow didn't seem to exist before this project.",
        epilog="Authored by @M-Davies. Please submit feedback and bug reports to https://github.com/M-Davies/cis-github-benchmark"
    )
    parser.add_argument(
        "-t", "--token",
        help="A GitHub PAT for the organisation to audit",
        required=True
    )
    parser.add_argument(
        "-u", "--url",
        help="Root URL of the GitHub instance. Defaults to https://api.github.com",
        default="https://api.github.com"
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Increase verbosity, will report progress for each request",
        action="store_true"
    )
    parser.add_argument(
        "-q", "--quiet",
        help="No output to the console (log and report file output is still present), only errors will be shown",
        action="store_true"
    )
    parser.add_argument(
        "-r", "--report",
        help="Produces a pretty report file containing the discovered findings and recommendations. Defaults to a timestamped file in the current directory but you can specify a path instead",
        default=f"{datetime.now().strftime('%d-%m-%Y-%H-%M-%S')}_cis_benchmark"
    )
    parser.add_argument(
        "-l", "--log",
        help="Produces a log file of verbose and non-verbose debug information. Defaults to a timestamped file in the current directory"
    )
    localArgs = parser.parse_args()
    
    # Setup logging
    if localArgs.verbose is True:
        LOGGER.setLevel(logging.INFO)
    else:
        LOGGER.setLevel(logging.WARN)
    
    if localArgs.quiet is False:
        LOG_OUTPUT_HANDLER = logging.StreamHandler(sys.stderr)
        LOG_OUTPUT_HANDLER.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        LOGGER.addHandler(LOG_OUTPUT_HANDLER)
    
    if localArgs.log is not None:
        LOG_FILE_HANDLER = logging.FileHandler(filename=f"{datetime.now().strftime('%d-%m-%Y-%H-%M-%S')}_cis_benchmark.log", encoding="utf-8", mode="a")
        LOG_FILE_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
        LOGGER.addHandler(LOG_FILE_HANDLER)

    return localArgs

def benchmark():
    # Login to GitHub instance
    g = Github(base_url=ARGS.url, login_or_token=ARGS.token)
    if g.get_user().login is None:
        LOGGER.exception(f"FAILED to login to {ARGS.url} with the provided token")
    else:
        LOGGER.info(f"Successfully logged into {ARGS.url} as {g.get_user().login}")
    
    # Begin benchmark checks
    

if __name__ == "__main__":
    ARGS = parseArgs()
    benchmark()
