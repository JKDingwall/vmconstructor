__all__ = []

import abc
import json
import logging
import os
import stat
import subprocess
import time
import uuid

# TODO:
#  - make the architecture a parameter
#  - add a reuse/force build parameter

DEFAULT_UBUNTU_ARCHIVE = "http://gb.archive.ubuntu.com/ubuntu/"


class ImageNotReady(Exception):
    """\
    Raise if a request to clone the image is made but the image build has not completed.
    """
    pass



class _imageBase(object, metaclass=abc.ABCMeta):
    def __init__(self, subvol):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._subvol = subvol

        self._status = None
        self._loadStatus()


    @property
    @abc.abstractmethod
    def _imagecls(self):
        """\
        The _image class that this _bootstrap generates.
        """
        pass


    @property
    def path(self):
        return(self._subvol.path)


    def _loadStatus(self):
        if not self._status:
            self._logger.debug("Attempting to load status from {sf}".format(sf=os.path.join(self._subvol.path, "status.json")))
            try:
                with open(os.path.join(self._subvol.path, "status.json"), "rb") as fp:
                    self._status = json.loads(fp.read().decode(encoding="UTF-8"))
            except FileNotFoundError:
                # Initialise the status file
                self._status = {
                    "uuid": str(uuid.uuid4()),
                    "progress": {},
                    "activity": []
                }
                self._saveStatus()


    def _saveStatus(self):
        with open(os.path.join(self._subvol.path, "status.json"), "wb") as fp:
            fp.write(bytes(json.dumps(self._status, indent=2), "UTF-8"))


    def getStatus(self):
        try:
            return(self._status["progress"]["status"])
        except Exception:
            return("notready")


    def setStatus(self, status):
        self._status["progress"] = {
            "status": status,
            "timestamp": time.time()
        }
        self._saveStatus()


    def logActivity(self, activity, data):
          self._status["activity"].append({
              "time": time.time(),
              "activity": activity,
              "data": data
          })
          self._saveStatus()


    def solidify(self, disks):
        """\
        Finalise the image to disk volumes.
        """
        pass


    def clone(self, name):
        """\
        Clone this image to the given name an _image class for it.
        """
        if self.getStatus() != "complete":
            raise ImageNotReady()

        try:
            # Try to snapshot this volume to the given name
            img = self._imagecls(self._subvol.snapshot(name))
            img._status["origin"]["uuid"] = self._status["uuid"]
            img._saveStatus()
            return(img)
        except FileExistsError:
            # The path exists, assume it is already a snapshot of this vm so compare the origin uuid to confirm
            img = self._imagecls(self._subvol._parent.create(name))
            if self._status["uuid"] == img._status["origin"]["uuid"]:
                return(img)
            else:
                # The existing snapshot is not derived from the current parent
                raise




class _bootstrap(_imageBase, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def bootstrap(self, *args, **kw):
        """\
        This method should take the empty volume and build a basic image in it.
        """
        pass



class _image(_imageBase, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def _prepareChroot(self):
        pass


    @abc.abstractmethod
    def _unprepareChroot(self):
        pass


    @abc.abstractmethod
    def update(self):
        """\
        This method should take an existing image and run the necessary commands to bring
        the installed packages up to their latest versions.
        """
        pass


    @abc.abstractmethod
    def install(self, *args):
        """\
        Install the packages given as an argument.
        """
        pass


    def newUUID(self):
        """\
        Change the uuid of this vm image
        """
        self._status["uuid"] = str(uuid.uuid4())
        self._saveStatus()


    def execChroot(self, *args):
        """\
        Execute the array of commands in the chroot environment.
        """
        try:
            self._prepareChroot()
            for cmd in args:
                self._logger.debug("Executing chroot command in {p}: {cmd}".format(p=os.path.join(self._subvol.path, "origin"), cmd=cmd))
                self.logActivity("chroot", cmd)
                subprocess.check_call(["chroot", os.path.join(self._subvol.path, "origin")] + cmd)
        except Exception:
            raise
        finally:
            self._unprepareChroot()


    def applyTemplates(self, tpldir):
        """\
        Find templates in tpldir and apply them to the image.
        """
        pass


    def applyPayload(self, payload):
        """\
        Apply a payload package + script.
        """
        pass



class debootstrap(_bootstrap):
    @property
    def _imagecls(self):
        return(ubuntu)

    def bootstrap(self, release, archive=None):
        self._release = release
        self._imagepath = os.path.join(self._subvol.path, "origin")

        if not archive:
            archive = DEFAULT_UBUNTU_ARCHIVE

        # Split this to foreign / second step
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

        self._status["origin"] = {
            "release": release,
            "archive": archive,
            "uuid": self._status["uuid"]
        }
        self._saveStatus()


        if self.getStatus() == "complete":
            self._logger.info("A completed image was found, skipping debootstrap")
            return
        elif self.getStatus() in ["interrupted", "failed", "notready"]:
            self._logger.info("A previously failed build exists, restarting")
            self._subvol.reset()
        else:
            self._logger.error("")

        self._logger.debug("Executing debootstrap with command: {cmd}".format(cmd=cmd))
        self.logActivity("bootstrap", cmd)
        try:
            start = time.time()
            self.setStatus("building")
            subprocess.check_call(cmd)
            self.setStatus("complete")
        except (KeyboardInterrupt):
            self.setStatus("interrupted")
            raise
        except (Exception):
            self.setStatus("failed")
        finally:
            # Make sure any potential mounts are cleaned up
            subprocess.call(["umount", os.path.join(self._imagepath, "proc")])
            subprocess.call(["umount", os.path.join(self._imagepath, "sys")])
            self._logger.info("Build ended after {s}s".format(s=time.time()-start))



class ubuntu(_image):
    chroot_bind = ["dev", "dev/pts", "proc", "sys"]
    policydsh = """\
#!/bin/bash

# James Dingwall
# Suppress startup of services during install to avoid conflicting
# with build server.

ALLARGS="${@}"

while : ; do
    case "${1}" in
    -*)
        shift
        ;;
    makedev)
        exit 0
        ;;
    *)
        if [ "${2}" = "start" ] || [ "${2}" = "restart" ] ; then
            echo "info: vmconstruct suppressed action: ${ALLARGS}"
            exit 101
        else
            exit 0
        fi
        ;;
    esac
done
"""

    @property
    def _imagecls(self):
        return(ubuntu)


    def _prepareChroot(self):
        # Mounts for filesystems
        for mnt in self.chroot_bind:
            subprocess.check_call(["mount", "-o", "bind", os.path.join(os.sep, mnt), os.path.join(self._subvol.path, "origin", mnt)])
        # Create a policy.d file to suppress service startup and +x
        with open(os.path.join(self._subvol.path, "origin", "usr", "sbin", "policy-rc.d"), "wb") as fp:
            fp.write(self.policydsh.encode("utf-8"))
        os.chmod(os.path.join(self._subvol.path, "origin", "usr", "sbin", "policy-rc.d"), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


    def _unprepareChroot(self):
        try:
            # Remove policy.d file
            os.unlink(os.path.join(self._subvol.path, "origin", "usr", "sbin", "policy-rc.d"))
        except FileNotFoundError:
            # Don't worry if the file is missing
            pass
        # Umounts for filesystems
        for mnt in reversed(self.chroot_bind):
            subprocess.check_call(["umount", "-l", os.path.join(self._subvol.path, "origin", mnt)])


    def update(self):
        self.setStatus("updating")
        self.newUUID()
        self.execChroot(
            ["apt-get", "update"],
            ["apt-get", "-y", "upgrade"]
        )
        self.setStatus("complete")


    def install(self, *args):
        self._logger.debug("Installing packages: {a}".format(a=args))
        self._logger.warning("Support arbitrary arguments for apt-get command")
        self.execChroot(*[["apt-get", "-y", "install", x] for x in args])
