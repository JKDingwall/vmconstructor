#!/usr/bin/env python3

# James Dingwall
# DMUK

from __future__ import print_function

import unittest

try:
    from vmconstruct._tests import suite as vmconstruct_suite
except ImportError:
    print("Unable to complete imports, tests disabled")
    exit(0)


def suite():
    pkgTS = unittest.TestSuite(vmconstruct_suite())

    return(pkgTS)


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())

