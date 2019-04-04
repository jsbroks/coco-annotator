import subprocess
import requests


COMMITS = "https://api.github.com/repos/jsbroks/coco-annotator/commits/{}"
COMPARE = "https://api.github.com/repos/jsbroks/coco-annotator/compare/{}...{}"

CURRENT_VERSION = ""
LATEST_VERSION = ""


def get_tag():
    result = subprocess.run(["git", "describe", "--abbrev=0", "--tags"], stdout=subprocess.PIPE)
    return str(result.stdout.decode("utf-8")).strip()


def get_current():
    result = subprocess.run(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE)
    return str(result.stdout.decode("utf-8")).strip()


def get_branch():
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout=subprocess.PIPE)
    return str(result.stdout.decode("utf-8")).strip()


class VersionControl:

    def __init__(self):
        self.valid = True

        self.branch = get_branch()
        self.current_version = get_current()
        self.tag = get_tag()

        self.latest_version = self.get_latest()
        self.commits_behind = self.get_commits_behind()

    def is_latest(self):
        if len(self.current_version) > 0 and len(self.latest_version):
            return self.current_version == self.latest_version

        return False

    def get_latest(self):
        r = requests.get(COMMITS.format(self.branch))

        if r.status_code != requests.codes.ok:
            self.valid = False
            return ""

        return r.json().get('sha')

    def get_commits_behind(self):

        if self.current_version == self.latest_version or not self.valid:
            return 0

        r = requests.get(COMPARE.format(self.latest_version, self.current_version))

        if r.status_code != requests.codes.ok:
            self.valid = False
            return 0

        return r.json().get('behind_by')
