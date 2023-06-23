from github import Github
import logging

def getUsersRepos(LOGGER: logging.getLogger(), G: Github):
    return [repo for repo in G.get_user("M-Davies").get_repos() if repo.fork is False]

