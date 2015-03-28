# -*- coding: utf-8 -*-
"""\
.. module:: vmconstruct.bootstrap.payloads
    :platform: Unix
    :synopsis: vmconstruct payload installation manager

.. moduleauthor:: James Dingwall <james@dingwall.me.uk>

This module manages the execution of payload scripts in a
chroot path.
"""

import contextlib
import logging
import os
import shutil
import subprocess
import tempfile

from ..exceptions import *



class applyplds(object):
    """\
    This class provides a context manager which can run over a list
    of directories and create as many apply() context managers as
    necessary.
    """
    def __init__(self, image, *plds, chrootpath=None):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)

        self._image = image
        if chrootpath is None:
            self._chrootpath = os.path.join(image._subvol._path, "origin")
        else:
            self._chrootpath = chrootpath
        self._plds = plds
        self._appliers = [apply(self._image, p, self._chrootpath) for p in self._plds]


    @contextlib.contextmanager
    def apply(self):
        with contextlib.ExitStack() as stack:
            [stack.enter_context(applier) for applier in self._appliers]
            # TODO: Reverse the order of the items on the stack so the exit
            # is in the same order as the entry.
            yield



class apply(object):
    """\
    This class implements a context manager which will apply the
    pre script if it exists on entry, and the post script on exit.
    """
    def __init__(self, image, payload, chrootpath):
        """\
        The constructor.

        :param image: The image instance that this payload is being applied for.
        :type image: vmconstruct.bootstrap._image.
        :param payload: A directory containing a payload to be applied to the image.
        :type payload: str.
        :param chroot: The directory where the chroot image is mounted.
        :type chroot: str.
        """
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__+":"+payload)
        self._image = image
        self._payload = payload
        self._chrootpath = chrootpath


    def __enter__(self):
        """\
        Enter using the context manager, apply pre script.
        """
        self._logger.debug("__enter__()")
        self._logger.debug("Applying payload")
        self._tdir = tempfile.mkdtemp(dir=os.path.join(self._chrootpath, "tmp"))
        rsync = [
            "rsync",
            "-avHAX",
            self._payload + "/",
            self._tdir
        ]
        subprocess.check_call(rsync)
        if os.path.exists(os.path.join(self._tdir, "pre")):
            self._image.execChroot(["sh", "-c", "cd {tdir} && exec ./pre".format(tdir=os.path.join(*self._tdir.split(os.sep)[-2:]))], chrootpath=self._chrootpath)


    def __exit__(self, *exc_info):
        """\
        Exit using the context manager, apply post script.  If we are exiting
        are exiting due to an exception we will not call the apply function.
        The directory will be removed on exit.
        """
        self._logger.debug("__exit__()")
        if any(exc_info):
            return(False)

        if os.path.exists(os.path.join(self._tdir, "post")):
            self._image.execChroot(["sh", "-c", "cd {tdir} && exec ./post".format(tdir=os.path.join(*self._tdir.split(os.sep)[-2:]))], chrootpath=self._chrootpath)
        shutil.rmtree(self._tdir)
