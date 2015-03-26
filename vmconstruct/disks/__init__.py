# -*- coding: utf-8 -*-
__all__ = [
    "disks",
    "disk"
]

import logging
import os
import re
import stat
import subprocess
from sparse_list import SparseList

from . import partition


class disks(object):
    def __init__(self, subvol, disksyml):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._subvol = subvol
        self._disks = {}

        for (k, v) in disksyml.items():
            self._disks[k] = disk(subvol, k, v)


    def format(self):
        """\
        Format all disks.
        """
        for (k, v) in self._disks.items():
            v.format()


    def mount(self):
        """\
        Mount all disks and return the / of the mount path.
        """
        self._logger.error("TODO: use context manager for mounting")
        for (mount, disk) in sorted([(m, v) for (k, v) in self._disks.items() for m in v.mounts]):
            disk.mount(mount)

        return(os.path.join(self._subvol.path, "mnt"))


    def umount(self):
        """\
        Umount all disks.
        """
        for (mount, disk) in reversed(sorted([(m, v) for (k, v) in self._disks.items() for m in v.mounts])):
            disk.umount(mount)



class disk(object):
    class _losetup(SparseList):
        """\
        Manage the loopback preparation of the disk.
        """
        def __init__(self, id, _disk):
            SparseList.__init__(self, 0)
            self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__+"({nm})".format(nm=id))
            self._disk = _disk
            self._unmap = False


        def __enter__(self):
            self._logger.debug("__enter__ context manager")
            self._unmap = self.losetup()


        def __exit__(self, *exc_info):
            self._logger.debug("__exit__ context manager")
            if self._unmap:
                self.ulosetup()

            return(False)


        def clear(self):
            self.elements.clear()
            self.size = 0


        def losetup(self):
            """\
            Execute losetup to map the partitions in the image file to devices.
            """
            if not len(self):
                cmd = ["kpartx", "-avs", self._disk.image]
                self._logger.debug("Mapping image partitions: {cmd}".format(cmd=cmd))
                loopre = re.compile("^loop([0-9]+)p([0-9]+)$")
                for l in subprocess.check_output(cmd).decode(encoding="UTF-8").splitlines():
                    m = re.search("^loop[0-9]+p([0-9]+)$", l.split()[2])
                    self[int(m.group(1))] = ("/dev/mapper/"+l.split()[2], l.split()[7])

                return(True)
            else:
                return(False)


        def ulosetup(self):
            """\
            Unmap mapped partitions.
            """
            if len(self):
                cmd = ["kpartx", "-dvs", self._disk.image]
                self._logger.debug("Unmapping image partitions: {cmd}".format(cmd=cmd))
                subprocess.check_output(cmd)
                self.clear()



    def __init__(self, subvol, id, defn):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._parts = SparseList(0)
        self._lo = self._losetup(id, self)
        self._mounts = {}
        self._subvol = subvol

        # mbr or gpt
        label = defn.get("label", "gpt")
        if label == "mbr":
            self._pt = partition.mbr()
        elif label == "gpt":
            self._pt = partition.gpt()
        else:
            raise Exception("Unknown disk partition table type")


        # add partitions
        parts = defn.get("partitions", {})
        if not isinstance(parts, dict):
            parts = {}

        for (idx, part) in parts.items():
            if "name" in part:
                name = part["name"]
            elif "label" in part:
                name = part["label"]
            else:
                name = None

            self._parts[idx] = (part["size"], part["filesystem"], part.get("mount", None), part.get("label", None))
            self._pt.addPartition(idx, part["size"], part.get("partcode", part["filesystem"]), name=name, flags=part.get("flags", []))

        try:
            os.makedirs(os.path.join(self._subvol.path, "disks"))
        except FileExistsError:
            if not os.path.isdir(os.path.join(self._subvol.path, "disks")):
                raise

        # Use fs to compress the image on disk
        #os.chflags(os.path.join(self._subvol.path, "disks"), stat.UF_COMPRESSED)
        #subprocess.check_call(["chattr", "+c", os.path.join(self._subvol.path, "disks")])

        self.image = os.path.join(self._subvol.path, "disks", "{id}.img".format(id=id))
        self._pt.makeDisk(self.image)


    def losetup(self):
        return(self._lo.losetup())


    def ulosetup(self):
        return(self._lo.ulosetup())


    def format(self):
        """\
        Format the partitions for the requested filesystem.
        """
        with self._lo:
            self._logger.error("TODO: support aribtrary fs args")
            for (k, (mapper, loop)) in self._lo.elements.items():
                (size, filesystem, mount, label) = self._parts[k]
                if filesystem == "esp":
                    cmd = ["mkfs", "-t", "vfat", "-n", "EFI_SYSTEM", "-F", "32", mapper]
                else:
                    cmd = ["mkfs", "-t", filesystem, mapper]
                self._logger.debug("Formatting disk {size}Mb partition {k}: {cmd}".format(size=size, k=k, cmd=cmd))
                print(subprocess.check_output(cmd).decode(encoding="UTF-8"))


    @property
    def mounts(self):
        """\
        Return the mount points defined on this disk.
        """
        return(sorted([mount for (k, (size, filesystem, mount, label)) in self._parts.elements.items()]))


    def mount(self, mounts=None):
        """\
        Mount the filesytems at mnt under the disk subvolume
        """

        self.losetup()

        if mounts:
            mounts = [mounts]
        else:
            mounts = self.mounts

        for mount in mounts:
            mnt = os.path.join(self._subvol.path, "mnt", mount[1:])
            try:
                os.makedirs(mnt)
            except FileExistsError:
                if not os.path.isdir(mnt):
                    raise

            k = [k for (k, (s, f, m, l)) in self._parts.elements.items() if m == mount].pop()
            (mapper, loop) = self._lo[k]

            cmd = ["mount", mapper, mnt]
            self._logger.debug("Mounting filesystem: {cmd}".format(cmd=cmd))
            subprocess.check_call(cmd)
            self._mounts[mnt] = mapper


    def umount(self, mounts=None):
        if mounts:
            mounts = [mounts]
        else:
            mounts = reversed(self.mounts)

        for mount in mounts:
            mnt = os.path.join(self._subvol.path, "mnt", mount[1:])
            if mnt in self._mounts:
                cmd = ["umount", mnt]
                self._logger.debug("Umounting filesystem: {cmd}".format(cmd=cmd))
                subprocess.check_call(cmd)
                del(self._mounts[mnt])

        if not len(self._mounts.keys()):
            self.ulosetup()
