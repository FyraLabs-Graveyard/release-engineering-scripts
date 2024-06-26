# koji watcher thread
from asyncio import tasks
from genericpath import exists
import koji
import threading
import time
import umreleng.logger as logger
import sys
import os

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


class KojiWatcher(threading.Thread):
    def __init__(self, task_id):
        threading.Thread.__init__(self)
        self.task = task_id
        self.logger = logger.logger
        self.name = f"Kojiwatcher for task {self.task}"
        self.koji = koji.ClientSession("https://lapis.ultramarine-linux.org/kojihub")

    def run(self, *args, **kwargs):
        task_state = object
        while self.is_alive():
            task = self.koji.getTaskInfo(self.task)
            if task["state"] == koji.TASK_STATES["FREE"]:
                # check task_state if it's still free
                if task_state == koji.TASK_STATES["FREE"]:
                    # if task is still free, wait for a bit and check again
                    time.sleep(5)
                else:
                    task_state = koji.TASK_STATES["FREE"]
                    self.logger.info(f"Task {self.task} is now free")
                    time.sleep(5)
                continue
            elif task["state"] == koji.TASK_STATES["OPEN"]:
                # check task_state if it's still open
                if task_state == koji.TASK_STATES["OPEN"]:
                    # if task is still open, wait for a bit and check again
                    time.sleep(5)
                else:
                    task_state = koji.TASK_STATES["OPEN"]
                    self.logger.info(f"Task {self.task} is now open")
                    time.sleep(5)
            elif task["state"] == koji.TASK_STATES["CLOSED"]:
                self.logger.info(f"Task {self.task} is closed")
                self.stop()
            elif task["state"] == koji.TASK_STATES["ASSIGNED"]:
                if task_state == koji.TASK_STATES["ASSIGNED"]:
                    # if task is still assigned, wait for a bit and check again
                    time.sleep(5)
                else:
                    task_state = koji.TASK_STATES["ASSIGNED"]
                    self.logger.info(f"Task {self.task} is now assigned")
                    time.sleep(5)
            elif task["state"] == koji.TASK_STATES["FAILED"]:
                self.logger.info(f"Task {self.task} has failed")
                sys.exit(1)
            else:
                self.logger.info(f'Task {self.task} is in state {task["state"]}')
                time.sleep(5)

    def stop(self):
        self.running = False
        sys.exit(0)
