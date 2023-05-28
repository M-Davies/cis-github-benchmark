# cis-github-benchmark

A CIS benchmark audit tool for GitHub environments, because it somehow didn't seem to exist before this project.

## Setup

- Clone this repo (obviously):
```
git clone https://github.com/M-Davies/cis-github-benchmark.git
```
- The project was developed using Python 3.11.3. It is recommended you use [pyenv](https://github.com/pyenv/pyenv) to install a supported Python version.
  - You're probably safe to use any version above 3.7, which is currently the minimum supported version of [PyGithub](https://github.com/PyGithub/PyGithub).
- Install dependencies and verify installation with:
```shell
cd cis-github-benchmark/
python -m pip install -r requirements.txt
python cis-github-benchmark.py --help
```

