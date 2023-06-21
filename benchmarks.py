import logging
from github import Github

# GLOBALS
G = Github
LOGGER = logging.getLogger()

def test_1_1_3_codereview():
    pass # TODO


def runBenchmarks(benchmarks: list, g: Github, logger: logging.getLogger()):
    # Setup Globals
    global G, LOGGER
    G = g
    LOGGER = logger

    # Run through benchmark list
    failedMarks = []
    for currentBenchmark in benchmarks:
        benchmarkResult = {"id": currentBenchmark, "passed": False, "message": ""}

        if currentBenchmark == "1.1.3":
            LOGGER.info("Testing benchmark 1.1.3 (Ensure any change to code receives approval of two strongly authenticated users)...")
            benchmarkResult = test_1_1_3_codereview()

        # Evaluate result
        if benchmarkResult.passed is True:
            LOGGER.info(f"Benchmark {currentBenchmark} PASSED!")
        else:
            LOGGER.error(f"Benchmark {currentBenchmark} FAILED!\n{benchmarkResult.message}")
            failedMarks.append(benchmarkResult)

    return failedMarks
