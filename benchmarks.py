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

def checkBranchProtections(repo: Repository, repoResult: dict):
    response = repoResult
    if response.protections is None:
        # No protections at all
        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. No branch protections were enforced on the default branch ({repo.default_branch})")
    elif response.protections.required_pull_request_reviews is None:
        # Branch protections enabled but no PR reviews required
        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull request reviews were not required on the default branch ({repo.default_branch})")
        response["reviews_required"] = False
    else:
        # Check required approving reviews
        if response.protections.required_pull_request_reviews.required_approving_review_count <= 1:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull requests against branch {repo.default_branch} do not require 2 or more approvers before merging (approvers required = {response.protections.required_pull_request_reviews.required_approving_review_count})")
            response["reviewers"] = response.protections.required_pull_request_reviews.required_approving_review_count
        else:
            LOGGER.info(f"[{repo.full_name}] : Branch protections OK!")
    return response

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
        LOGGER.info(f"Retrieved target repositories = ({[repo.full_name + ',' for repo in repos]})")

    # Run through benchmark list
    failedMarks = []
    if reposPresent is True:
        for currentRepo in repos:
            LOGGER.info(f"Benchmarking {currentRepo.full_name}...")

            # Check branch protections
            LOGGER.info(f"[{currentRepo.full_name}] : Checking branch protections...")
            repoResult = {
                "repo": currentRepo.name,
                "branch": currentRepo.default_branch,
                "protections": getBranchProtections(currentRepo),
                "reviews_required": True,
                "reviewers": 2
            }
            repoResult = checkBranchProtections(currentRepo, repoResult)
            
            
            # Evaluate result
            if benchmarkResult is True:
                LOGGER.info(f"[{currentRepo.full_name}] : Benchmark {currentBenchmark} PASSED!")
            else:
                failedMarks.append({"id": currentBenchmark, "result": benchmarkResult})

    return failedMarks
