import logging
import base64
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from github import Github, Repository, Organization, GithubException

# GLOBALS
G = Github
LOGGER = logging.getLogger()

def isOrganisation(possibleOrg: str):
    # Determine if we're working with a user or an organisation
    if G.get_user().login == possibleOrg:
        return True
    else:
        return False

def getValidRepos(forks: bool, organisation: str):
    repos = []
    # Determine if we're targeting a user or an organisation
    target = organisation
    if isOrganisation(organisation) is True:
        target = G.get_user().login
    # Filter out repos
    if forks is False:
        repos = [repo for repo in G.get_user(target).get_repos() if repo.fork is False]
    else:
        repos = G.get_user(target).get_repos()
    return repos

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

def checkBranchProtections(repo: Repository, benchmarks: list):
    response = {}
    protections = getBranchProtections(repo)
    if protections is None:
        # No protections at all
        message = f"[{repo.full_name}] : Benchmark 1.1.20 FAILED. No branch protections are enforced on the default branch ({repo.default_branch})"
        LOGGER.error(message)
        response["no_protections"][repo.full_name] = message
    elif protections.required_pull_request_reviews is None:
        # Branch protections enabled but no PR reviews required
        message = f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull request reviews are not required on the default branch ({repo.default_branch})"
        LOGGER.error(message)
        response["reviews_required"][repo.full_name] = message
    else:
        # Check required approving reviews
        if protections.required_pull_request_reviews.required_approving_review_count <= 1:
            message = f"[{repo.full_name}] : Benchmark 1.1.3 FAILED. Pull requests against branch {repo.default_branch} do not require 2 or more approvers before merging (approvers required = {protections.required_pull_request_reviews.required_approving_review_count})"
            LOGGER.error(message)
            response["reviewers"][repo.full_name] = message
        
        # Check dismiss stale reviews
        if protections.required_pull_request_reviews.dismiss_stale_reviews is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.4 FAILED. Pull request reviews against branch {repo.default_branch} are not dismissed when new commits are pushed"
            LOGGER.error(message)
            response["stale_dismissed"][repo.full_name] = message
        
        # Check dismissal users
        if protections.required_pull_request_reviews.dismissal_users is [] and protections.required_pull_request_reviews.dismissal_teams is []:
            message = f"[{repo.full_name}] : Benchmark 1.1.5 FAILED. Users are not prevented from dismissing code change reviews"
            LOGGER.error(message)
            response["restrict_dismiss"][repo.full_name] = message
        else:
            repoCollaborators = getRepoCollaborators(repo)
            if protections.required_pull_request_reviews.dismissal_users is not []:
                for dismissalUser in protections.required_pull_request_reviews.dismissal_users:
                    if dismissalUser not in repoCollaborators:
                        message = f"[{repo.full_name}] : Benchmark 1.1.5 FAILED. A user ({dismissalUser.login}) is authorised to dismiss code change reviews but is not a repository or organisation admin."
                        LOGGER.error(message)
                        response["dismiss_non_admin"][repo.full_name].append(message)
            else:
                message = f"[{repo.full_name}] : Benchmark 1.1.5 FAILED. No users are authorised to dismiss code change reviews, pull request owners are able to ignore code reviews after changes were made"
                LOGGER.error(message)
                response["dismiss_non_admin"][repo.full_name] = message
        
        # Check required review from code owners
        if protections.required_pull_request_reviews.require_code_owner_reviews is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.7 FAILED. Trusted code owners are not required to review and approve code change proposals made to their respective owned areas in the code base"
            LOGGER.error(message)
            response["trusted_owners_required"][repo.full_name] = message
        
        # Check branches up to date and required status checks before merging enabled
        try:
            if protections.required_status_checks.strict is False:
                message = f"[{repo.full_name}] : Benchmark 1.1.10 FAILED. Pull requests with outdated code can be tested by status checks"
                LOGGER.error(message)
                response["required_status_checks_strict"][repo.full_name] = message
        except KeyError:
            message = f"[{repo.full_name}] : Benchmark 1.1.9 FAILED. Pull requests can be merged before status checks pass"
            LOGGER.error(message)
            response["required_status_checks"][repo.full_name] = message

        # Check open comments resolved before accept
        if protections.required_conversation_resolution is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.11 FAILED. Open conversations do not have to be resolved before the pull request can be merged"
            LOGGER.error(message)
            response["required_conversation_resolution"][repo.full_name] = message
        
        # Check commits must be signed
        if repo.default_branch.get_required_signatures() is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.12 FAILED. Signed commits are not compulsory"
            LOGGER.error(message)
            response["signed_commits"][repo.full_name] = message
        
        # Check linear history enforced
        if protections.required_linear_history is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.13 FAILED. Linear History is not enforced"
            LOGGER.error(message)
            response["linear_history"][repo.full_name] = message

        # Check branch protections enforced on administrators
        if protections.enforce_admins.enabled is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.14 FAILED. Branch protections are not enforced for repository or organisation admins"
            LOGGER.error(message)
            response["enforce_admins"][repo.full_name] = message
        
        # TODO: Figure out what to do for 1.1.15, "trusted users and teams" could mean anything

        # Check force pushing is denied
        if protections.allow_force_pushes.enabled is True:
            message = f"[{repo.full_name}] : Benchmark 1.1.16 FAILED. Force pushing is permitted"
            LOGGER.error(message)
            response["force_pushing_disabled"][repo.full_name] = message
        
        # Check branch deletions are denied
        if protections.allow_deletions.enabled is True:
            message = f"[{repo.full_name}] : Benchmark 1.1.17 FAILED. Branch deletions are permitted"
            LOGGER.error(message)
            response["branch_deleting_disabled"][repo.full_name] = message
    
    return response

def checkFileContents(repo: Repository, benchmarks: list):
    response = {}
    # Check codeowners file is present
    codeOwners = getFileContents(repo, "CODEOWNERS")
    if codeOwners is None:
        codeOwners = getFileContents(repo, "docs/CODEOWNERS")
        if codeOwners is None:
            codeOwners = getFileContents(repo, ".github/CODEOWNERS")
            if codeOwners is None:
                message = f"[{repo.full_name}] : Benchmark 1.1.6 FAILED. No CODEOWNERS file is present in the repository's root, docs/ or .github/ directories"
                LOGGER.error(message)
                response["codeowners"][repo.full_name] = message
    
    # Check security policy is present
    securityPolicy = getFileContents(repo, "SECURITY.md")
    if securityPolicy is None:
        message = f"[{repo.full_name}] : Benchmark 1.2.1 FAILED. No SECURITY.md file is present in the root directory of the repository"
        LOGGER.error(message)
        response["security_policy"][repo.full_name] = message

    return response

def checkRepo(repo: Repository, benchmarks: list):
    response = {}
    # Check stale branches
    for branch in repo.get_branches():
        latestCommit = datetime.strptime(repo.get_commit(branch.commit.sha).created_at)
        # TODO: This may be broken, double check this works
        if datetime.now() >= datetime.now() + relativedelta(months=-3):
            message = f"[{repo.full_name}] : Benchmark 1.1.8 FAILED. {branch.name} is a stale branch (latest commit was > 3 months ago on {latestCommit.strftime('%d/%m/%Y, %H:%M:%S')})"
            LOGGER.error(message)
            response["stale_branches"][repo.full_name].append(message)
    
    # Check there is a scanning workflow
    workflows = repo.get_workflows()
    if workflows == []:
        message = f"[{repo.full_name}] : Benchmark 1.1.18 FAILED. No workflows are present in the repository"
        LOGGER.error(message)
        response["workflows"][repo.full_name] = message
    else:
        foundWorkflow = False
        for workflow in workflows:
            workflowConfig = getFileContents(repo, workflow.path)
            # TODO: Currently no way to check if it actually scans code, this just makes sure the branch appears in the workflow config
            if f"branches:[\"{repo.default_branch}\"]" in re.sub(r"[\n\t\s]*", "", workflowConfig):
                foundWorkflow = True
                break
        if foundWorkflow is False:
            message = f"[{repo.full_name}] : Benchmark 1.1.18 FAILED. No workflows were identified that scanned the repository's default branch"
            LOGGER.error(message)
            response["workflows"][repo.full_name] = message

    return response

def checkOrganisation(organisation: Organization, benchmarks: list):
    response = {}
    # Check repo creation is limited
    if organisation.members_can_create_public_repositories is True:
        message = f"[{organisation.login}] : Benchmark 1.2.2 FAILED. Members are allowed to create public repositories under the organisation"
        LOGGER.error(message)
        response["public_repos"][organisation.login] = message
    if organisation.members_can_create_private_repositories is True:
        message = f"[{organisation.login}] : Benchmark 1.2.2 FAILED. Members are allowed to create private repositories under the organisation"
        LOGGER.error(message)
        response["private_repos"][organisation.login] = message

    return response


def runBenchmarks(
    benchmarks: list,
    g: Github,
    logger: logging.getLogger(),
    forks: bool,
    organisation: str
):
    # Setup
    global G, LOGGER
    G = g
    LOGGER = logger

    # Filter out valid repos
    LOGGER.info(f"Fetching repositories for {G.get_user().login}...")
    repos = getValidRepos(forks, organisation)
    reposPresent = True
    if repos == []:
        LOGGER.warn(f"User {g.get_user().login} does not possess readable repositories with this token, some benchmark checks may be unavailable!")
        reposPresent = False
    else:
        LOGGER.info(f"Retrieved target repositories = ({[repo.full_name + ',' for repo in repos]})")

    # Check organisational benchmarks
    failedMarks = {}
    if isOrganisation(organisation) is True:
        LOGGER.info(f"[{organisation}] : Checking organisation settings...")
        failedMarks.update(checkOrganisation(G.get_organization(organisation), benchmarks))
    else:
        LOGGER.warn(f"{G.get_user().login} appears to be a personal account. Organisation based checks will be skipped!")

    # Check repository benchmarks
    if reposPresent is True:
        for currentRepo in repos:
            LOGGER.info(f"Benchmarking {currentRepo.full_name}...")

            # Check branch protections
            LOGGER.info(f"[{currentRepo.full_name}] : Checking branch protections...")
            # TODO: Figure out a way to implement white/black listing here
            failedMarks.update(checkBranchProtections(currentRepo, benchmarks))
            LOGGER.info(f"[{currentRepo.full_name}] : Checking contents of files...")
            failedMarks.update(checkFileContents(currentRepo, benchmarks))
            LOGGER.info(f"[{currentRepo.full_name}] : Checking repository settings...")
            failedMarks.update(checkRepo(currentRepo, benchmarks))

            # Evaluate result
    else:
        LOGGER.warn(f"No repositories are present for {organisation}. Repository based checks will be skipped!")

    return failedMarks
