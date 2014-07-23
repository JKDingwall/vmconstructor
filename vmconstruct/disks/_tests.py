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
import time
import unittest
import yaml

from vmconstruct.btrfs import subvolume
from vmconstruct.disks import disk, disks
from vmconstruct.disks.partition_tests import suite as partition_suite


def suite():
    pkgTS = unittest.TestSuite()

    pkgTS.addTest(partition_suite())

    pkgTS.addTest(DisksUT("emptyGptDisk"))
    pkgTS.addTest(DisksUT("onePartGptDisk"))
    pkgTS.addTest(DisksUT("formatGptDisk"))
    pkgTS.addTest(DisksUT("mountGptDisk"))

    pkgTS.addTest(DisksUT("format2GptDisks"))
    pkgTS.addTest(DisksUT("mount2GptDisks"))

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
      mount: /
""")
        d = disk(self.disksvol.create("onePartGptDisk"), "test", diskdfn)


    def formatGptDisk(self):
        diskdfn = yaml.load("""\
  label: gpt
  partitions:
    1:
      size: 1024
      filesystem: ext3
      mount: /
    2:
      size: 512
      filesystem: ext4
      mount: /home
""")
        d = disk(self.disksvol.create("formatGptDisk"), "test", diskdfn)
        d.format()

    def mountGptDisk(self):
        diskdfn = yaml.load("""\
  label: gpt
  partitions:
    1:
      size: 1024
      filesystem: ext3
      mount: /
    2:
      size: 512
      filesystem: ext4
      mount: /home
""")
        d = disk(self.disksvol.create("mountGptDisk"), "test", diskdfn)
        d.format()
        d.mount()
        time.sleep(5)
        d.umount()


    def format2GptDisks(self):
        disksdfn = yaml.load("""\
test1:
  label: gpt
  partitions:
    1:
      size: 1024
      filesystem: ext3
      mount: /
    2:
      size: 512
      filesystem: ext4
      mount: /home
test2:
  label: gpt
  partitions:
    1:
      size: 512
      filesystem: xfs
      mount: /var
    2:
      size: 512
      filesystem: btrfs
      mount: /tmp
    3:
      size: 512
      filesystem: ext4
      mount: /home/ftp
""")
        d = disks(self.disksvol.create("format2GptDisks"), disksdfn)
        d.format()


    def mount2GptDisks(self):
        disksdfn = yaml.load("""\
test1:
  label: gpt
  partitions:
    1:
      size: 1024
      filesystem: ext3
      mount: /
    2:
      size: 512
      filesystem: ext4
      mount: /home
test2:
  label: gpt
  partitions:
    1:
      size: 512
      filesystem: xfs
      mount: /var
    2:
      size: 512
      filesystem: btrfs
      mount: /tmp
    3:
      size: 512
      filesystem: ext4
      mount: /home/ftp
""")
        d = disks(self.disksvol.create("mount2GptDisks"), disksdfn)
        d.format()
        d.mount()
        time.sleep(5)
        d.umount()



if __name__ == "__main__":
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s: [%(levelname)s]%(name)s - %(message)s')
    stderr_log_handler = logging.StreamHandler()
    stderr_log_handler.setFormatter(formatter)
    logger.addHandler(stderr_log_handler)
    logger.setLevel(getattr(logging, "DEBUG"))

    runner = unittest.TextTestRunner()
    runner.run(suite())
