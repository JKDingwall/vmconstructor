#!/usr/bin/env python3

LOG_LEVEL = "DEBUG"

import logging
import unittest
from random import choice

if __name__ != "__main__":
    from .partition import msdos, PartitionTooLarge


def suite():
    partitionTS = unittest.TestSuite()
    partitionTS.addTest(PartitionUT("msdos_empty"))
    partitionTS.addTest(PartitionUT("msdos_1part"))
    partitionTS.addTest(PartitionUT("msdos_12part"))
    partitionTS.addTest(PartitionUT("msdos_13part"))
    partitionTS.addTest(PartitionUT("msdos_toolarge"))
    partitionTS.addTest(PartitionUT("msdos_toooffset"))

    return(partitionTS)


class PartitionUT(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s: [%(levelname)s]%(name)s - %(message)s')
        stderr_log_handler = logging.StreamHandler()
        stderr_log_handler.setFormatter(formatter)
        self.logger.addHandler(stderr_log_handler)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))


    def msdos_empty(self):
        self.logger.info("Testing the creation of an empty msdos mbr partition table")

        testfile = "/tmp/msdos_empty.img"

        pt = msdos()
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def msdos_1part(self):
        self.logger.info("Testing the creation of an msdos mbr partition table with one partition")

        testfile = "/tmp/msdos_1part.img"

        pt = msdos()
        pt.addPartition(1, 8, 0x83, bootable=True)
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def msdos_12part(self):
        self.logger.info("Testing the creation of an msdos mbr partition table with partitions 1 and 2")

        testfile = "/tmp/msdos_12part.img"

        pt = msdos()
        pt.addPartition(1, 8, 0x83)
        pt.addPartition(2, 16, 0x83, bootable=True)
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def msdos_13part(self):
        self.logger.info("Testing the creation of an msdos mbr partition table with partitions 1 and 3")

        testfile = "/tmp/msdos_13part.img"

        pt = msdos()
        pt.addPartition(1, 8, 0x83, bootable=True)
        pt.addPartition(3, 12, 0x83, bootable=False)
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def msdos_toolarge(self):
        self.logger.info("Trying to make a 3Tb partition")

        pt = msdos()
        self.assertRaises(PartitionTooLarge, pt.addPartition, 1, 3*1024*1024, 0x83)


    def msdos_toooffset(self):
        self.logger.info("Trying to make a partition starting beyond 2Tb")

        pt = msdos()
        pt.addPartition(1, 1*1024*1024, 0x83)
        pt.addPartition(2, int(1.5*1024*1024), 0x83)
        self.assertRaises(PartitionTooLarge, pt.addPartition, 3, 64*1024, 0x83)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


if __name__ == "__main__":
    from partition import msdos, PartitionTooLarge

    runner = unittest.TextTestRunner()
    runner.run(suite())
