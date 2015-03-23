# -*- coding: utf-8 -*-
"""\

.. module:: vmconstruct.exceptions
    :platform: Unix
    :synopsis: Exceptions

.. moduleauthor:: James Dingwall <james@dingwall.me.uk>

"""

from __future__ import print_function

__all__ = [
    "VMCBaseError",
    "VMCPhaseError",
    "VMCTemplateChecksumError",
    "VMCImageNotReadyError",
    "VMCImageDatedError"
]


class VMCBaseError(Exception):
    """\
    The VMConstruct Base Error.
    """


class VMCPhaseError(VMCBaseError):
    """\
    This exception is raised by a template if the application
    phase is not relevant.
    """


class VMCTemplateChecksumError(VMCBaseError):
    """\
    This exception is raised when the template tries to replace a file
    with a checksum that is not recognised.
    """


class VMCImageNotReadyError(VMCBaseError):
    """\
    Raise if a request to clone the image is made but the image build has not completed.
    """


class VMCImageDatedError(VMCBaseError):
    """\
    Raise if a child image is out of date wrt to the parent
    """

