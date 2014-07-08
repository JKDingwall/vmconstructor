#!/usr/bin/env python3

""":"
python3 "${0}" "${@}"
":"""

import unittest

from vmconstruct._tests import suite as vmconstruct_suite


def suite():
        pkgTS = unittest.TestSuite(vmconstruct_suite())

        return(pkgTS)


if __name__ == "__main__":
        runner = unittest.TextTestRunner()
        runner.run(suite())
