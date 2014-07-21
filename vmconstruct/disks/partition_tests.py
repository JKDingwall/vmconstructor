#!/bin/bash

""":"
if [ "$(dirname ${0})" = "." ] ; then
    PP="$(pwd)/../.."
fi

PYTHONPATH="${PP}" exec /usr/bin/env python3 "${0}"
":"""

LOG_LEVEL = "DEBUG"

import logging
import unittest
from random import choice

from vmconstruct.disks.partition import gpt, mbr, PartitionTooLarge, InvalidPartitionNumber


def suite():
    partitionTS = unittest.TestSuite()
    partitionTS.addTest(PartitionUT("mbr_empty"))
    partitionTS.addTest(PartitionUT("mbr_1part"))
    partitionTS.addTest(PartitionUT("mbr_12part"))
    partitionTS.addTest(PartitionUT("mbr_13part"))
    partitionTS.addTest(PartitionUT("mbr_toolarge"))
    partitionTS.addTest(PartitionUT("mbr_toooffset"))

    partitionTS.addTest(PartitionUT("gpt_empty"))
    partitionTS.addTest(PartitionUT("gpt_1part"))
    partitionTS.addTest(PartitionUT("gpt_nparts"))
    partitionTS.addTest(PartitionUT("gpt_badpart"))

    return(partitionTS)



class PartitionUT(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))


    def mbr_empty(self):
        self.logger.info("Testing the creation of an empty mbr mbr partition table")

        testfile = "/tmp/mbr_empty.img"

        pt = mbr()
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def mbr_1part(self):
        self.logger.info("Testing the creation of an mbr mbr partition table with one partition")

        testfile = "/tmp/mbr_1part.img"

        pt = mbr()
        pt.addPartition(1, 8, 0x83, flags=["bootable"])
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def mbr_12part(self):
        self.logger.info("Testing the creation of an mbr mbr partition table with partitions 1 and 2")

        testfile = "/tmp/mbr_12part.img"

        pt = mbr()
        pt.addPartition(1, 8, 0x83)
        pt.addPartition(2, 16, 0x83, flags=["bootable"])
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def mbr_13part(self):
        self.logger.info("Testing the creation of an mbr mbr partition table with partitions 1 and 3")

        testfile = "/tmp/mbr_13part.img"

        pt = mbr()
        pt.addPartition(1, 8, 0x83, flags=["bootable"])
        pt.addPartition(3, 12, 0x83, flags=[])
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def mbr_toolarge(self):
        self.logger.info("Trying to make a 3Tb partition")

        pt = mbr()
        self.assertRaises(PartitionTooLarge, pt.addPartition, 1, 3*1024*1024, 0x83)


    def mbr_toooffset(self):
        self.logger.info("Trying to make a partition starting beyond 2Tb")

        pt = mbr()
        pt.addPartition(1, 1*1024*1024, 0x83)
        pt.addPartition(2, int(1.5*1024*1024), 0x83)
        self.assertRaises(PartitionTooLarge, pt.addPartition, 3, 64*1024, 0x83)


    def gpt_empty(self):
        pt = gpt()

        self.logger.info("Testing the creation of an empty guid partition table")

        testfile = "/tmp/gpt_empty.img"

        pt = gpt()
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def gpt_1part(self):
        pt = gpt()

        self.logger.info("Testing the creation of a guid partition table with 1 partition")

        testfile = "/tmp/gpt_1part.img"

        pt = gpt()
        pt.addPartition(1, 512, "linux/filesystem", "a test name")
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def gpt_nparts(self):
        pt = gpt()

        self.logger.info("Testing the creation of a guid partition table with some partitions")

        testfile = "/tmp/gpt_nparts.img"

        pt = gpt()
        for x in range(choice(range(1, 129))):
            pt.addPartition(x, 16, "linux/filesystem", "a test name")
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def gpt_badpart(self):
        pt = gpt()

        self.logger.info("Testing the creation of a guid partition table with 1 partition")

        testfile = "/tmp/gpt_1part.img"

        pt = gpt()
        self.assertRaises(InvalidPartitionNumber, pt.addPartition, 129, 512, "linux/filesystem", "a test name")
        pt.makeDisk(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")



if __name__ == "__main__":
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s: [%(levelname)s]%(name)s - %(message)s')
    stderr_log_handler = logging.StreamHandler()
    stderr_log_handler.setFormatter(formatter)
    logger.addHandler(stderr_log_handler)
    logger.setLevel(getattr(logging, "INFO"))

    runner = unittest.TextTestRunner()
    runner.run(suite())
