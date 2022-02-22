#!/usr/bin/env python3

# Mass rebuild script

# from the Ultramarine Release Engineering script collection

# Does a mass rebuild for a new release.

from genericpath import exists
from glob import glob
import shutil
import koji
import os
import subprocess
import logging
import umreleng.koji as kojiThread
import pygit2
import gitlab

logger = logging.getLogger("ultramarine-massbuild")

formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def noRebuild(pkg, reason):
    # logs the package name and appends it to NOREBUILD
    # check if line with pkg name already exists in NOREBUILD
    # if NOREBUILD doesnt exist, create it
    if not exists("./NOREBUILD"):
        with open("./NOREBUILD", "w+") as f:
            f.write(pkg)
    with open("./NOREBUILD", "r+") as f:
        if pkg in f.read():
            return True
        else:
            f.write(f"{pkg}: {reason}" + "\n")
            return


profile = koji.get_profile_module("koji")  # the profile to start compose with
session = profile.ClientSession(profile.config.server)
session.gssapi_login()

tag = "um36"
user = "Ultramarine Release Tracking Service"
creds = pygit2.credentials.KeypairFromAgent('git')

comment = f"Mass rebuild for release {tag}"
workdir = os.path.join(os.getcwd(), "workdir")
# create workdir if it doesn't exist
if not exists(workdir):
    os.mkdir(workdir)

# callbacks
class GitCallback(pygit2.RemoteCallbacks):
    def credentials(self, url, username_from_url, allowed_types):
        if allowed_types & pygit2.credentials.GIT_CREDENTIAL_USERNAME:
            return pygit2.Username('git')
        # password authentication
        if allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY:
            return pygit2.KeypairFromAgent('git')
        return None
    def push_update_reference(self, refname, message):
        logger.info(f"Pushing update to {refname}, {message}") 


# foo = session.getRepo('um36-build')
gl = gitlab.Gitlab(url="https://gitlab.ultramarine-linux.org", private_token="")
# list all packages in the tag
group = gl.groups.get(id=8)
pkgs = session.listPackages(tagID=tag)
for package in pkgs:
    pkgname = package["package_name"]
    # If it ends with "Live", then it's a live image, remove it
    if pkgname.endswith("Live"):
        logger.info(f"{pkgname} seems to be a live image, will skip and ignore.")
        continue
    logger.info("Processing package: " + pkgname)
    pkg_repo = group.projects.list(search=pkgname)
    # pkgrepo returns as a list
    # check if list empty
    if len(pkg_repo) == 0:
        logger.warning(f"Package {pkgname} not found on Gitlab, will not be rebuilt.")
        noRebuild(pkgname, "not found on Gitlab")
        continue
    else:
        # check for each repo if the name matches the package name
        for pkg in pkg_repo:
            if pkg.path_with_namespace.split("/")[1] == pkgname:
                # if the name matches, get the repo
                pkg_repo = pkg.attributes
            # if not then look for the next repo
            else:
                continue
            # if there's still no repo, then the package is not on Gitlab
            if not pkg_repo:
                logger.warning(f"Package {pkgname} not found on Gitlab, will not be rebuilt.")
                noRebuild(pkgname, "not found on Gitlab")
                continue
    logger.debug(pkg_repo["http_url_to_repo"])
    logger.debug(pkg_repo["ssh_url_to_repo"])
    # replace ssh port with 2222
    sshport = pkg_repo["ssh_url_to_repo"].replace(" ssh://git@", "ssh://git@:2222/")
    logger.info(f"Cloning {pkgname}")
    try:
        git = pygit2.clone_repository(
            pkg_repo["ssh_url_to_repo"], os.path.join(workdir, pkgname)
            , callbacks=GitCallback(credentials=creds)
        )
    # except if the repo is already cloned
    except ValueError:
        logger.debug(f"{pkgname} already cloned, will use existing repo")
        try:
            git = pygit2.Repository(os.path.join(workdir, pkgname))
        except Exception as e:
            logger.error(f"Error cloning {pkgname}: {e}. Skipping.")
            noRebuild(pkgname, "error cloning repo: " + str(e))
            continue
    except pygit2.GitError as e:
        logger.error(f"{pkgname} failed to clone: {e}")
        continue
    # get the latest commit
    try:
        commit = git.revparse_single("HEAD").hex
    except KeyError:
        logger.warning(f"{pkgname} is an empty repo!, skipping")
        noRebuild(pkgname, "empty repo")
        continue
    # logger.debug(f'Latest commit for {pkgname} is {commit}')
    # create a new branch on the cloned repo
    try:
        git.create_branch(tag, git.revparse_single("HEAD"))
        logger.info(f"Created branch {tag} for {pkgname}")
        # get the latest commit for the branch
        commit = git.revparse_single("HEAD").hex
    except ValueError:
        logger.info(f"{pkgname} already has a branch {tag}, will use this one")
        commit = git.revparse_single("HEAD").hex
    logger.debug(f"Latest commit for {pkgname} is {commit}")
    # checkout to the branch
    try:
        branch = git.lookup_branch(tag)
        ref = git.lookup_reference(branch.name)
        git.checkout(ref)
    except pygit2.GitError as e:
        logger.error(f"{pkgname} failed to checkout {tag}: {e}")
        noRebuild(pkgname, "error checking out branch: " + str(e))
        continue
    # enter git workdir
    os.chdir(os.path.join(workdir, pkgname))
    # find the first spec file
    spec = glob("*.spec")
    if len(spec) == 0 or len(spec) > 1:
        logger.error(f"{pkgname} has more than one spec file, will not be rebuilt.")
        noRebuild(pkgname, "more than one spec file")
        continue
    else:
        spec = spec[0]
    subprocess.run(["rpmdev-bumpspec", "-c", comment, "-u", user, spec])
    # create a new commit with the bumped spec file
    git.index.add_all()
    git.index.write()
    tree = git.index.write_tree()
    author = pygit2.Signature(user, "releng@ultramarine-linux.org")
    committer = pygit2.Signature(user, "releng@ultramarine-linux.org")
    # ref is the branch we are on
    ref = git.lookup_reference(branch.name)
    # commit the new commit
    commit = git.create_commit(ref.name, author, committer, comment, tree, [ref.target])
    logger.debug(f"made commit for {pkgname}")
    # go back up
    os.chdir("../..")
    try:
        logger.info(f"Pushing {ref.name} for {pkgname}")
        for remote in git.remotes:
            if remote.name == "origin":
                os.system("pwd")
                os.chdir(os.path.join(workdir, pkgname))
                push = remote.push([ref.name], callbacks=GitCallback(credentials=creds))
    except pygit2.GitError as e:
        logger.error(f"{pkgname} failed to push: {e}")
        # if it's authention error exit the script
        if "authentication required" in str(e):
            logger.error(
                f"Authentication error for {pkgname}. Please set up authentication. This script will now clean up and exit."
            )
            # clean up workdir and exit
            shutil.rmtree(workdir)
            exit(1)
    except Exception as e:
        logger.error(f"{pkgname} failed to push: {e}")
        continue
    # format the URL for the koji build
    url = f'git+{pkg_repo["http_url_to_repo"]}#{commit}'
    logger.debug(f"URL for {pkgname} is {url}")
    build = session.build(src=url, target=tag, opts={"scratch": False})
    kojiThread.KojiWatcher(build).start()
