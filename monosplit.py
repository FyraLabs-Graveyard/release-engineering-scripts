#!/usr/bin/env python3

# RPM monorepo splitter script

# from the Ultramarine Release Engineering script collection

# Splits an RPM monorepo into multiple RPM spec repos.
# Made for use with umpkg (https://gitlab.ultramarine-linux.org/release-engineering/umpkg) and GitLab

# as always, everything is under the MIT license (https://opensource.org/licenses/MIT)
# Copyright (c) 2022, Cappy Ishihara and Co. Do as you will as long as you credit me.
# Written mostly with the help of GitHub Copilot (https://copilot.github.com), becuase looking up documentation is a waste of time. Comes with the added benefit of this entire script being annotated!

# Your file structure should look like this:
#  - foo.spec
#  - bar.spec
#  - patches/
#       - foo/
#          foo.patch
#       - bar/
#          bar.patch

# EXISTING REPOS WILL BE OVERWRITTEN

import os
import gitlab
import configparser


config = configparser.ConfigParser()

token = ""  # Reminder to NEVER push your token to a public repo or we'll get hacked, I will dox you (jk)
instance = "https://gitlab.ultramarine-linux.org"
branch = "um36"
gl = gitlab.Gitlab(url=instance, private_token=token)

# Batch create gitlab project in dist-pkgs/

# for each .spec file
for file in os.listdir("."):
    if file.endswith(".spec"):
        print("found spec file: " + file)
        # get the file name without the .spec
        name = file.split(".")[0]
        # create the project in group 'dist-pkgs' which id is 8
        try:
            print("Creating project: " + name)
            projectc = gl.projects.create({"name": name, "namespace_id": 8})
            print(projectc.get_id())
            # get the project id of the new project
            projectid = projectc.get_id()
        except gitlab.exceptions.GitlabCreateError as e:
            # if project has already been taken, continue pushing
            # the error is a json object
            print(e)
            error = str(e)
            if "has already been taken" in error:
                print(e)
                print("Project already exists, continuing")
                # get the project ID from path dist-pkgs/{name}
                project = gl.projects.list(search=name)[0]
                print(project.get_id())
                projectid = project.get_id()
                pass
            else:
                print(e)
                continue
        print("Created project: " + name)
        # create a folder here with the name of the project
        print("Creating folder: " + name)
        os.mkdir(name)
        # move the spec file to the folder
        print("Moving spec file: " + file)
        os.rename(file, name + "/" + file)
        # look in the patches/folder for a folder with the same name as the project
        print("Looking for patches in patches/" + name)
        for patch in os.listdir("patches"):
            if patch == name:
                # move all the files in the folder to the project folder
                for file in os.listdir("patches/" + patch):
                    os.rename("patches/" + patch + "/" + file, name + "/" + file)
                    print("Moved file: " + file)
            # if the folder doesnt exist, skip it
            else:
                continue
        # create the git repo in the project folder
        os.chdir(name)
        # make a config file with a [umpkg] section
        # get the https url of the project
        http_url = gl.projects.get(projectid).http_url_to_repo
        print("Creating config file")
        with open("umpkg.cfg", "w") as configfile:
            try:
                config.add_section("umpkg")
            except Exception as e:
                print(e)
                pass
            config.set(
                "umpkg",
                "git_repo",
                f"https://gitlab.ultramarine-linux.org/dist-pkgs/{name}.git",
            )
            # write the config file as umpkg.cfg
            config.write(configfile)
        print("Creating git repo")
        os.system("git init --initial-branch=main")
        os.system("git add .")
        os.system(
            'git commit -m "Automated project split from RPM monorepo by batchcreate.py"'
        )
        # get the SSH url of the project
        url = f"ssh://git@gitlab.ultramarine-linux.org:2222/dist-pkgs/{name}.git"
        os.system("git remote add origin " + url)
        # create a branch in the git repo with the name of the branch variable
        print("push to remote")
        os.system("git branch " + branch)
        os.system("git push --force --set-upstream origin " + "main")
        # move back to the root folder
        os.chdir("..")
