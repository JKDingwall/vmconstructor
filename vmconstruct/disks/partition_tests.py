#!/usr/bin/env python3

LOG_LEVEL = "DEBUG"

import logging
import unittest
from random import choice

if __name__ != "__main__":
    from .partition import msdos


def suite():
    partitionTS = unittest.TestSuite()
    partitionTS.addTest(PartitionUT("msdos_empty"))
    partitionTS.addTest(PartitionUT("msdos_1part"))

    return(partitionTS)


class PartitionUT(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s: [%(levelname)s]%(name)s - %(message)s')
        stderr_log_handler = logging.StreamHandler()
        stderr_log_handler.setFormatter(formatter)
        self.logger.addHandler(stderr_log_handler)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))


    def mksparse(self, file, sizemb):
        sparse = open(file, "ab")
        sparse.truncate(sizemb*1048576)
        sparse.close()


    def msdos_empty(self):
        self.logger.info("Testing the creation of an empty msdos mbr partition table")

        testfile = "/tmp/msdos_empty.img"

        self.mksparse(testfile, 16)
        pt = msdos()
        pt.write(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


    def msdos_1part(self):
        self.logger.info("Testing the creation of an msdos mbr partition table with one partition")

        testfile = "/tmp/msdos_1part.img"

        self.mksparse(testfile, 16)
        pt = msdos()
        pt.addPartition(1, 8, 0x83)
        pt.write(testfile)

        self.logger.info("Review the result with another paritioning tool to confirm the result")


if __name__ == "__main__":
    from partition import msdos

    runner = unittest.TextTestRunner()
    runner.run(suite())
