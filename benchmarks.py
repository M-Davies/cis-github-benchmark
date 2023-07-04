import logging
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta
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

def getRepoCollaborators(repo: Repository):
    try:
        return repo.get_collaborators()
    except GithubException:
        # No collaborators
        return None
    
def getFileContents(repo: Repository, path: str):
    return str(base64.decodebytes(repo.get_content(path=path, ref=repo.default_branch).content))

def checkBranchProtections(repo: Repository, repoResult: dict, benchmarks: list):
    response = repoResult
    if response.protections is None:
        # No protections at all
        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. No branch protections are enforced on the default branch ({repo.default_branch})")
    elif response.protections.required_pull_request_reviews is None:
        # Branch protections enabled but no PR reviews required
        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull request reviews are not required on the default branch ({repo.default_branch})")
        response["reviews_required"] = False
    else:
        # Check required approving reviews
        if response.protections.required_pull_request_reviews.required_approving_review_count <= 1:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull requests against branch {repo.default_branch} do not require 2 or more approvers before merging (approvers required = {response.protections.required_pull_request_reviews.required_approving_review_count})")
            response["reviewers"] = response.protections.required_pull_request_reviews.required_approving_review_count
        
        # Check dismiss stale reviews
        if response.protections.required_pull_request_reviews.dismiss_stale_reviews is False:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.4 FAILED. Pull request reviews against branch {repo.default_branch} are not dismissed when new commits are pushed")
            response["stale_dismissed"] = False
        
        # Check dismissal users
        if response.protections.required_pull_request_reviews.dismissal_users is [] and response.protections.required_pull_request_reviews.dismissal_teams is []:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.5 FAILED. Users are not prevented from dismissing code change reviews")
            response["restrict_dismiss"] = False
        else:
            repoCollaborators = getRepoCollaborators(repo)
            if response.protections.required_pull_request_reviews.dismissal_users is not []:
                for dismissalUser in response.protections.required_pull_request_reviews.dismissal_users:
                    if dismissalUser not in repoCollaborators:
                        LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.5 FAILED. A user ({dismissalUser.login}) is authorised to dismiss code change reviews but is not a repository or organisation admin.")
                        response["dismiss_non_admin"].append(dismissalUser.login)
            else:
                LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.5 FAILED. No users are authorised to dismiss code change reviews, pull request owners are able to ignore code reviews after changes were made")
                response["dismiss_non_admin"] = False
        
        # Check required review from code owners
        if response.protections.required_pull_request_reviews.require_code_owner_reviews is False:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.7 FAILED. Trusted code owners are not required to review and approve code change proposals made to their respective owned areas in the code base")
            response["trusted_owners_required"] = False
        
        # Check branches up to date and required status checks before merging enabled
        try:
            if response.protections.required_status_checks.strict is False:
                LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.10 FAILED. Pull requests with outdated code can be tested by status checks")
                response["required_status_checks_strict"] = False
        except KeyError:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.9 FAILED. Pull requests can be merged before status checks pass")
            response["required_status_checks"] = False

        # Check open comments resolved before accept
        if response.protections.required_conversation_resolution is False:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.11 FAILED. Open conversations do not have to be resolved before the pull request can be merged")
            response["required_conversation_resolution"] = False
        
        # Check commits must be signed
        if repo.default_branch.get_required_signatures() is False:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.12 FAILED. Signed commits are not compulsory")
            response["signed_commits"] = False
        
        # Check linear history enforced
        if response.protections.required_linear_history is False:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.13 FAILED. Linear History is not enforced")
            response["linear_history"] = False

        # Check branch protections enforced on administrators
        if response.protections.enforce_admins.enabled is False:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.14 FAILED. Branch protections are not enforced for repository or organisation admins")
            response["enforce_admins"] = False
        
        # TODO: Figure out what to do for 1.1.15, "trusted users and teams" could mean anything

        # Check force pushing is denied
        if response.protections.allow_force_pushes.enabled is True:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.16 FAILED. Force pushing is permitted")
            response["force_pushing_disabled"] = False
        
        # Check branch deletions are denied
        if response.protections.allow_deletions.enabled is True:
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.17 FAILED. Branch deletions are permitted")
            response["branch_deleting_disabled"] = False
    
    return response

def checkFileContents(repo: Repository, repoResult: dict, benchmarks: list):
    response = repoResult
    # Check codeowners file is present
    codeOwners = getFileContents(repo, "CODEOWNERS")
    if codeOwners is None:
        codeOwners = getFileContents(repo, "docs/CODEOWNERS")
        if codeOwners is None:
            codeOwners = getFileContents(repo, ".github/CODEOWNERS")
            if codeOwners is None:
                LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.6 FAILED. No CODEOWNERS file is present in the root, docs/ or .github/ locations in the repository")
                response["codeowners"] = False
    return response

def checkRepo(repo: Repository, repoResult: dict, benchmarks: list):
    response = repoResult
    # Check stale branches
    for branch in repo.get_branches():
        latestCommit = datetime.strptime(repo.get_commit(branch.commit.sha).created_at)
        # TODO: This may be broken, double check this works
        if datetime.now() >= datetime.now() + relativedelta(months=-3):
            LOGGER.error(f"[{repo.full_name}] : Benchmark 1.1.8 FAILED. {branch.name} is a stale branch (latest commit was > 3 months ago on {latestCommit.strftime('%d/%m/%Y, %H:%M:%S')})")
            response["stale_branches"].append(branch.name)


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
                "reviewers": 2,
                "stale_dismissed": True,
                "restrict_dismiss": True,
                "dismiss_non_admin": [],
                "trusted_owners_required": True,
                "codeowners": True,
                "stale_branches": [],
                "required_status_checks_strict": True,
                "required_status_checks": True,
                "required_conversation_resolution": True,
                "signed_commits": True,
                "linear_history": True,
                "enforce_admins": True,
                "force_pushing_disabled": True,
                "branch_deleting_disabled": True
            }
            # TODO: Figure out a way to implement white/black listing here
            repoResult = checkBranchProtections(currentRepo, repoResult, benchmarks)
            repoResult = checkFileContents(currentRepo, repoResult, benchmarks)
            repoResult = checkRepo(currentRepo, repoResult, benchmarks)


            # Evaluate result
            if benchmarkResult is True:
                LOGGER.info(f"[{currentRepo.full_name}] : Benchmark {currentBenchmark} PASSED!")
            else:
                failedMarks.append({"id": currentBenchmark, "result": benchmarkResult})

    return failedMarks
