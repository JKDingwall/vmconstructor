__all__ = [
    "disks",
    "disk"
]

import logging
import os

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

            self._pt.addPartition(idx, part["size"], part.get("partcode", part["filesystem"]), name=name, flags=part.get("flags", []))

        try:
            os.makedirs(os.path.join(subvol.path, "disks"))
        except FileExistsError:
            if not os.path.isdir(os.path.join(subvol.path, "disks")):
                raise

        self._pt.makeDisk(os.path.join(subvol.path, "disks", "{id}.img".format(id=id)))
