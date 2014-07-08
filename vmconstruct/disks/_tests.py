#!/usr/bin/env python3

import unittest

from .partition_tests import suite as partition_suite

def suite():
    pkgTS = unittest.TestSuite()
    pkgTS.addTest(partition_suite())

    return(pkgTS)


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())

