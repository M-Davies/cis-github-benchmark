import logging
from github import Github, Repository, GithubException

# GLOBALS
G = Github
LOGGER = logging.getLogger()

def getBranchProtections(repo: Repository):
    try:
        return repo.get_branch(repo.default_branch).get_protection()
    except GithubException:
        # No protections are enabled
        return None

def checkBranchProtections(repo: Repository, failureResponse: dict):
    branchProtections = getBranchProtections(repo)
    if branchProtections is None:
        # No protections are enabled
        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. No branch protections were enforced on the default branch ({repo.default_branch})")
        failureResponse["protection"] = False
        return failureResponse
    elif branchProtections.required_pull_request_reviews is None:
        # Branch protections enabled but no PR reviews required
        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull request reviews were not required on the default branch ({repo.default_branch})")
        failureResponse["reviews_required"] = False
        return failureResponse
    else:
        # Check required approving reviews
        if branchProtections.required_pull_request_reviews.required_approving_review_count <= 1:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull requests against branch {repo.default_branch} do not require 2 or more approvers before merging (approvers required = {branchProtections.required_pull_request_reviews.required_approving_review_count})")
            failureResponse["reviewers"] = branchProtections.required_pull_request_reviews.required_approving_review_count
            return failureResponse
        else:
            return True

def test_1_1_4_stale_approvals(repo: Repository, failureResponse: dict):



def runBenchmarks(benchmarks: list, g: Github, logger: logging.getLogger(), forks: bool):
    # Setup
    global G, LOGGER
    G = g
    LOGGER = logger

    # Filter out valid repos
    LOGGER.info(f"Fetching repositories for {G.get_user().login}...")
    repos = []
    if forks is False:
        repos = [repo for repo in G.get_user(G.get_user().login).get_repos() if repo.fork is False]
    else:
        repos = G.get_user(G.get_user().login).get_repos()

    reposPresent = True
    if repos == []:
        LOGGER.warn(f"User {g.get_user().login} does not possess readable repositories with this token, some benchmark checks may be unavailable!")
        reposPresent = False
    else:
        LOGGER.info(f"Retrieved target repositories = {[repo.full_name for repo in repos]}")

    # Run through benchmark list
    failedMarks = []
    for currentRepo in repos:
        LOGGER.info(f"Benchmarking {currentRepo.full_name}...")
        # TODO: Don't need to enumerate through benchmarks, better to just pass on the valid list and pick and chose them as needed to save on processing power and time
        for currentBenchmark in benchmarks:
            # Check protections are alive first so we don't waste time on useless checks
            LOGGER.info(f"[{currentRepo.full_name}] : Checking benchmark {currentBenchmark}...")
            failureResult = {"repo": currentRepo.name, "branch": currentRepo.default_branch, "protections": getBranchProtections(currentRepo)}
            if failureResult.protections is None:
                LOGGER.error(f"[{currentRepo.full_name}] : Benchmark {currentBenchmark} FAILED. No branch protections were enforced on the default branch ({currentRepo.default_branch})")
                benchmarkResult = failureResult
            
            elif currentBenchmark == "1.1.3" and reposPresent is True:
                benchmarkResult = test_1_1_3_codereview(currentRepo, failureResult)
            elif currentBenchmark == "1.1.4" and reposPresent is True:
                benchmarkResult = test_1_1_4_stale_approvals(currentRepo, failureResult)
            # Evaluate result
            if benchmarkResult is True:
                LOGGER.info(f"[{currentRepo.full_name}] : Benchmark {currentBenchmark} PASSED!")
            else:
                failedMarks.append({"id": currentBenchmark, "result": benchmarkResult})

    return failedMarks
