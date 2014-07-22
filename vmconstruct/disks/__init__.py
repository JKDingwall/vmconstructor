__all__ = [
    "disks",
    "disk"
]

import logging
import os
import re
import subprocess
from sparse_list import SparseList

from . import partition


class disks(object):
    def __init__(self, subvol, disksyml):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._disks = {}

        for (k, v) in disksyml:
            self._disks[k] = disk(subvol, k, v)



class disk(object):
    def __init__(self, subvol, id, defn):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._lo = SparseList(0)
        self._parts = SparseList(0)

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

            self._parts[idx] = (part["size"], part["filesystem"], part.get("label", None))
            self._pt.addPartition(idx, part["size"], part.get("partcode", part["filesystem"]), name=name, flags=part.get("flags", []))

        try:
            os.makedirs(os.path.join(subvol.path, "disks"))
        except FileExistsError:
            if not os.path.isdir(os.path.join(subvol.path, "disks")):
                raise

        self._image = os.path.join(subvol.path, "disks", "{id}.img".format(id=id))
        self._pt.makeDisk(self._image)


    def losetup(self):
        """
        Execute losetup to map the partitions in the image file to devices.
        """
        if not len(self._lo):
            cmd = ["kpartx", "-avs", self._image]
            self._logger.debug("Mapping image partitions: {cmd}".format(cmd=cmd))
            loopre = re.compile("^loop([0-9]+)p([0-9]+)$")
            for l in subprocess.check_output(cmd).decode(encoding="UTF-8").splitlines():
                m = re.search("^loop[0-9]+p([0-9]+)$", l.split()[2])
                self._lo[int(m.group(1))] = ("/dev/mapper/"+l.split()[2], l.split()[7])


    def unlosetup(self):
        """
        Unmap mapped partitions.
        """
        if len(self._lo):
            cmd = ["kpartx", "-dvs", self._image]
            self._logger.debug("Unmapping image partitions: {cmd}".format(cmd=cmd))
            subprocess.check_output(cmd)


    def format(self):
        """
        Format the partitions for the requested filesystem.
        """
        self.losetup()
        for (k, (mapper, loop)) in self._lo.elements.items():
            (size, filesystem, label) = self._parts[k]
            cmd = ["mkfs", "-t", filesystem, mapper]
            self._logger.debug("Formatting disk {size}Mb partition {k}: {cmd}".format(size=size, k=k, cmd=cmd))
            try:
                print(subprocess.check_output(cmd).decode(encoding="UTF-8"))
            except Exception:
                pass

        self.unlosetup()
