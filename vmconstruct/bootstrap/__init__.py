# -*- coding: utf-8 -*-
__all__ = []

import abc
import copy
import json
import logging
import os
import shutil
import stat
import subprocess
import time
import uuid

from .payloads import applyplds
from .templates import applydirs
from ..exceptions import *
from ..disks import disks

# TODO:
#  - make the architecture a parameter
#  - add a reuse/force build parameter

DEFAULT_UBUNTU_ARCHIVE = "http://gb.archive.ubuntu.com/ubuntu/"


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


    def solidify(self, disksyml):
        """\
        Finalise the image to disk volumes.
        """
        for (dname, dparam) in disksyml.items():
            dtype = dparam.get("type", "hdd")
            if dtype == "squash":
                cmd = [
                    "mksquashfs",
                    os.path.join(self._subvol.path, "origin", *dparam["path"].split(os.sep)[1:]),
                    os.path.join(self._subvol.path, "{dname}.squashfs".format(dname=dname)),
                    "-comp",
                    "xz",
                    "-noappend"
                ]
                subprocess.check_call(cmd)
            elif dtype == "hdd":
                self._logger.warning("TODO: unimplmented hdd solidify")

                # Create a shallow copy of the disk definition to play with
                dparam = copy.copy(dparam)
                dparam.pop("type")

                # We support payloads during solidify to cover finalisation
                # of bootloader installations etc.
                payloads = dparam.pop("payloads", [])

                d = disks(self._subvol.create(dname), dparam)
                d.format()
                try:
                    mntpoint = d.mount()
                    cmd = ["rsync", "-avHAX", "--delete", "--progress", os.path.join(self._subvol.path, "origin")+"/", mntpoint+"/"]
                    print(subprocess.check_call(cmd))
                    with self.applypayloads(*payloads, chrootpath=mntpoint): pass
                finally:
                    d.umount()
            else:
                raise Exception("unsupported disk type")


    def open(self, name):
        """\
        Open a previously cloned image.
        """
        if self.getStatus() != "complete":
            raise VMCImageNotReadyError()

        img = self._imagecls(self._subvol._parent.create(name))
        if self._status["uuid"] == img._status["origin"]["uuid"]:
            return(img)
        else:
            raise VMCImageDatedError()


    def clone(self, name):
        """\
        Clone this image to the given name an _image class for it.
        """
        if self.getStatus() != "complete":
            raise VMCImageNotReadyError()

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
                ##raise VMCImageDatedError()
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
    def _prepareChroot(self, chrootpath=None):
        pass


    @abc.abstractmethod
    def _unprepareChroot(self, chrootpath=None):
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


    def execChroot(self, *args, chrootpath=None):
        """\
        Execute the array of commands in the chroot environment.
        """
        if chrootpath is None:
            chrootpath = os.path.join(self._subvol.path, "origin")

        try:
            self._prepareChroot(chrootpath=chrootpath)
            for cmd in args:
                self._logger.debug("Executing chroot command in {p}: {cmd}".format(p=chrootpath, cmd=cmd))
                self.logActivity("chroot", cmd)
                subprocess.check_call(["chroot", chrootpath] + cmd)
        finally:
            self._unprepareChroot(chrootpath=chrootpath)


    def applytemplates(self, ymlcfg, vmyml, *dirs):
        """\
        Find templates in tpldir and apply them to the image.
        """
        return(applydirs(self, ymlcfg, vmyml, *dirs).apply())


    def applypayloads(self, *payloads, chrootpath=None):
        """\
        Apply payload scripts to the image.
        """
        return(applyplds(self, *payloads, chrootpath=chrootpath).apply())



class debootstrap(_bootstrap):
    @property
    def _imagecls(self):
        return(ubuntu)


    def bootstrap(self, release, archive=None, proxy=None):
        self._release = release
        self._imagepath = os.path.join(self._subvol.path, "origin")

        if not archive:
            archive = DEFAULT_UBUNTU_ARCHIVE

        # Split this to foreign / second step
        cmdstg1 = [
            "/usr/sbin/debootstrap",
            "--verbose",
            "--variant=minbase",
            "--arch=amd64",
            "--components=main",
            "--foreign",
            "--include=lsb-release",
            release,
            self._imagepath,
            archive
        ]

        cmdstg2 = [
            "/usr/sbin/chroot",
            os.path.join(self._subvol.path, "origin"),
            "/debootstrap/debootstrap",
            "--second-stage"
        ]

        env = {}
        if proxy:
            os.environ["http_proxy"] = proxy
            env["http_proxy"] = proxy

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

        self._logger.debug("Executing debootstrap with command: {cmd}, environment: {env}".format(cmd=cmdstg1, env=env))
        self.logActivity("bootstrap", { "cmd": cmdstg1, "env": env })
        try:
            start = time.time()
            self.setStatus("building")
            subprocess.check_call(cmdstg1)
            # Additional work before packages installed here
            subprocess.check_call(cmdstg2)
            self.setStatus("complete")
        except (KeyboardInterrupt):
            self.setStatus("interrupted")
            raise
        except (Exception):
            self.setStatus("failed")
            raise
        finally:
            # Make sure any potential mounts are cleaned up
            subprocess.call(["umount", os.path.join(self._imagepath, "proc")])
            subprocess.call(["umount", os.path.join(self._imagepath, "sys")])
            self._logger.info("Build ended after {s}s".format(s=time.time()-start))



class ubuntu(_image):
    chroot_bind = ["dev", "dev/pts", "proc", "run", "sys"]
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


    def _prepareChroot(self, chrootpath=None):
        if chrootpath is None:
            chrootpath = os.path.join(self._subvol.path, "origin")

        # Mounts for filesystems
        for mnt in self.chroot_bind:
            subprocess.check_call(["mount", "-o", "bind", os.path.join(os.sep, mnt), os.path.join(chrootpath, mnt)])
        # Create a policy.d file to suppress service startup and +x
        with open(os.path.join(chrootpath, "usr", "sbin", "policy-rc.d"), "wb") as fp:
            fp.write(self.policydsh.encode("utf-8"))
        os.chmod(os.path.join(chrootpath, "usr", "sbin", "policy-rc.d"), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        # /proc/mtab
        shutil.copyfile("/etc/mtab", os.path.join(chrootpath, "etc", "mtab"))


    def _unprepareChroot(self, chrootpath=None):
        if chrootpath is None:
            chrootpath = os.path.join(self._subvol.path, "origin")

        # /proc/mtab
        os.unlink(os.path.join(chrootpath, "etc", "mtab"))
        try:
            # Remove policy.d file
            os.unlink(os.path.join(chrootpath, "usr", "sbin", "policy-rc.d"))
        except FileNotFoundError:
            # Don't worry if the file is missing
            pass
        # Umounts for filesystems
        for mnt in reversed(self.chroot_bind):
            subprocess.check_call(["umount", "-l", os.path.join(chrootpath, mnt)])


    def update(self, proxy=None):
        self.setStatus("updating")
        self.newUUID()
        if proxy:
            self.execChroot(
                ["apt-get", "update", "-o", "Acquire::http::Proxy={p}".format(p=proxy)],
                ["apt-get", "-y", "upgrade", "-o", "Acquire::http::Proxy={p}".format(p=proxy)]
            )
        else:
            self.execChroot(
                ["apt-get", "update"],
                ["apt-get", "-y", "upgrade"]
            )
        self.setStatus("complete")


    def install(self, *args, proxy=None, chrootpath=None):
        self._logger.debug("Installing packages: {a}".format(a=args))
        self._logger.warning("Support arbitrary arguments for apt-get command")
        self.execChroot(*[["apt-get", "-y", "install", x] for x in args], chrootpath=chrootpath)
