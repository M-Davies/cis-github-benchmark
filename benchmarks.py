import logging
from github import Github

import utilities

# GLOBALS
G = Github
LOGGER = logging.getLogger()

def test_1_1_3_codereview():
    # TODO: Need to find a better framework for feedback on multiple branches, could be done by expanding the branchResults variable to be hold a dict of all the info the report will need to be generated
    # TODO: Also add logging
    branchResults = []
    repos = utilities.getUsersRepos(LOGGER, G)
    for currentRepo in repos:
        branchProtections = currentRepo.get_branch(currentRepo.default_branch).get_protection()
        # Check required approving reviews
        if branchProtections.required_approving_review_count <= 1:
            failedMessage = f"Benchmark 1.1.3 FAILED on {currentRepo.url} : Pull requests against branch {currentRepo.default_branch} do not require 2 or more approvers before merging (approvers required = {branchProtections.required_approving_review_count})"
            LOGGER.error(failedMessage)
            branchResults.append({"repo": currentRepo.url, "branch": currentRepo.default_branch, "reviewers": branchProtections.required_approving_review_count})
    if branchResults == []:
        return True
    else:
        return branchResults



def runBenchmarks(benchmarks: list, g: Github, logger: logging.getLogger()):
    # Setup Globals
    global G, LOGGER
    G = g
    LOGGER = logger

    # Run through benchmark list
    failedMarks = []
    for currentBenchmark in benchmarks:
        if currentBenchmark == "1.1.3":
            LOGGER.info("Testing benchmark 1.1.3 (Ensure any change to code receives approval of two strongly authenticated users)...")
            benchmarkResult = test_1_1_3_codereview()

        # Evaluate result
        if benchmarkResult is True:
            LOGGER.info(f"Benchmark {currentBenchmark} PASSED!")
        else:
            LOGGER.error(f"Benchmark {currentBenchmark} FAILED!\n{benchmarkResult}")
            failedMarks.append(benchmarkResult)

    return failedMarks
