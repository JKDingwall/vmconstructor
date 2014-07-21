#!/bin/bash

""":"
if [ "$(dirname ${0})" = "." ] ; then
    PP="$(pwd)/../.."
fi

PYTHONPATH="${PP}" exec /usr/bin/env python3 ${0}
":"""

LOG_LEVEL = "DEBUG"
BTRFS = "/export/workspace"

import logging
import unittest
import yaml

from vmconstruct.btrfs import subvolume
from vmconstruct.disks import disk
from vmconstruct.disks.partition_tests import suite as partition_suite


def suite():
    pkgTS = unittest.TestSuite()

    pkgTS.addTest(partition_suite())

    pkgTS.addTest(DisksUT("emptyGptDisk"))
    pkgTS.addTest(DisksUT("onePartGptDisk"))

    return(pkgTS)



class DisksUT(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))

        rootvol = subvolume(BTRFS)
        testvol = rootvol.create("_tests")
        self.disksvol = testvol.create("disks")


    def emptyGptDisk(self):
        diskdfn = yaml.load("""\
  label: gpt
  partitions:
""")
        d = disk(self.disksvol.create("emptyGptDisk"), "test", diskdfn)


    def onePartGptDisk(self):
        diskdfn = yaml.load("""\
  label: gpt
  partitions:
    1:
      size: 1024
      filesystem: ext3
""")
        d = disk(self.disksvol.create("onePartGptDisk"), "test", diskdfn)


    def null(self):
        pass



if __name__ == "__main__":
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s: [%(levelname)s]%(name)s - %(message)s')
    stderr_log_handler = logging.StreamHandler()
    stderr_log_handler.setFormatter(formatter)
    logger.addHandler(stderr_log_handler)
    logger.setLevel(getattr(logging, "INFO"))

    runner = unittest.TextTestRunner()
    runner.run(suite())
