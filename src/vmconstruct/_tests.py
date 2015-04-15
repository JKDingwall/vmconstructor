#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from .disks._tests import suite as disks_suite

def suite():
    pkgTS = unittest.TestSuite()
    pkgTS.addTest(disks_suite())

    return(pkgTS)


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())

