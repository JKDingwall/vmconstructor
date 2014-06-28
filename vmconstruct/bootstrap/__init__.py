__all__ = []

import json
import logging
import os
import subprocess
import time

# TODO:
#  - make the architecture a parameter
#  - make the url for the release a parameter
#  - add a reuse/force build parameter

DEFAULT_ARCHIVE = "http://gb.archive.ubuntu.com/ubuntu/"

class debootstrap(object):
    def __init__(self, subvol, release, archive=None):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)

        self._release = release
        self._buildvol = subvol.create(release)
        self._imagepath = os.path.join(self._buildvol.path, "image")

        if not archive:
             archive = DEFAULT_ARCHIVE

        cmd = [
            "debootstrap",
            "--verbose",
            "--variant=minbase",
            "--arch=amd64",
            "--components=main",
            release,
            self._imagepath,
            archive
        ]

        self._status = {
            "build": {
                 "release": release,
                 "archive": archive,
                 "command": cmd
             }
        }

        self._logger.debug("Executing debootstrap with command: {cmd}".format(cmd=cmd))
        try:
            start = time.time()
            self.setStatus("building")
            subprocess.check_call(cmd)
            self.setStatus("complete")
        except (KeyboardInterrupt):
            # Make sure any potential mounts are cleaned up
            subprocess.call(["umount", os.path.join(self._imagepath, "proc")])
            subprocess.call(["umount", os.path.join(self._imagepath, "sys")])
            self.setStatus("interrupted")
            raise
        except (Exception):
            self.setStatus("failed")
        finally:
            self._logger.info("Build ended after {s}s".format(s=time.time()-start))


    def setStatus(self, status):
        self._status["progress"] = {
           "status": status,
           "timestamp": time.time()
        }

        with open(os.path.join(self._buildvol.path, "status.json"), "wb") as fp:
            fp.write(bytes(json.dumps(self._status, indent=2), "UTF-8"))


    @property
    def path(self):
        return(self._buildvol.path)
