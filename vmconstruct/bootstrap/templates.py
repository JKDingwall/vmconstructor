# -*- coding: utf-8 -*-
"""\
.. module:: vmconstruct.bootstrap.template
    :platform: Unix
    :synopsis: vmconstruct template manager

.. moduleauthor:: James Dingwall <james.dingwall@zynstra.com>

This is a program to manage the virtual machine state on the HAP.
"""

import contextlib
import hashlib
import logging
import os
from mako.exceptions import CompileException
from mako.template import Template

from ..exceptions import *



class applydirs(object):
    """\
    This class provides a context manager which can run over a list
    of directories and create as many apply() context managers as
    necessary.
    """
    def __init__(self, image, ymlcfg, vmyml, *dirs):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._image = image
        self._ymlcfg = ymlcfg
        self._vmyml = vmyml
        self._dirs = dirs
        self._appliers = [apply(self._image, self._ymlcfg, self._vmyml, d) for d in self._dirs]


    @contextlib.contextmanager
    def apply(self):
        with contextlib.ExitStack() as stack:
            [stack.enter_context(applier) for applier in self._appliers]
            yield



class apply(object):
    """\
    This class will apply templates to an image.  It is available as
    a context manager so we can apply templates before or
    after the image build otherwise it can be called manually to apply
    with a custom phase.

    If a template does not declare its phase in the install metadata
    then it is assumed that it is is idempotent and can be run
    multiple times without incident.
    """
    def __init__(self, image, ymlcfg, vmyml, tplpath):
        """\
        The constructor.

        :param subvol: The path to the image being constructed.
        :type imgpath: vmconstruct.bootstrap._image.
        :param tplpath: A directory containing template to be applied to the image.
        :type tplpath: str.
        """
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__+":"+tplpath)
        self._image = image
        self._ymlcfg = ymlcfg
        self._vmyml = vmyml
        self._tplpath = tplpath


    def __enter__(self):
        """\
        Enter using the context manager, apply POST phase templates.
        """
        self._logger.debug("__enter__()")
        self.install("PRE")


    def __exit__(self, *exc_info):
        """\
        Exit using the context manager, apply POST phase templates.  If we
        are exiting due to an exception we will not call the apply function.
        """
        self._logger.debug("__exit__()")
        if set(exc_info) == {None}:
            self.install("POST")
        else:
            return(False)


    def install(self, phase):
        """\
        Apply the templates in "phase" by searching in tplpath.
        """
        # TODO: installation file permissions/ownership
        if not os.path.isdir(self._tplpath):
            self._logger.warning("{td} is not a directory, ignoring for templating".format(td=self._tplpath))
            return

        self._logger.debug("Applying templates from {td}".format(td=self._tplpath))

        for (root, dirs, files) in os.walk(self._tplpath):
            for tplfile in [file for file in files if file.endswith(".tpl")]:
                with open(os.path.join(root, tplfile), "rb") as tplfp:
                    makot = Template(tplfp.read(), strict_undefined=True)

                install = {}
                makot.get_def("install").render(i=install)
                install["dest"] = os.path.join(self._image.path, "origin", *install["filename"].split(os.sep))

                try:
                    # Check the template is relevant to this phase of the build
                    if phase not in install["phase"]:
                        return
                except KeyError:
                    pass

                self._logger.debug("Installing {filename} from template to {dest}".format(**install))

                renderctx = {
                    "ymlcfg": self._ymlcfg,
                    "vmyml": self._vmyml,
                    "rootpath": os.path.join(self._image.path, "origin"),
                    "phase": phase
                }

                if os.path.isfile(install["dest"]):
                    # If there is an existing file at the location generate
                    # a checksum for it.  This can be used by a template to
                    # a) decide how to render content based on current source
                    # b) validate that the default file being replaced is the
                    #    the one template is relevant for, e.g. has upstream
                    #    made changes the template should account for.
                    s256 = hashlib.sha256()
                    with open(install["dest"], "rb") as fp:
                        while True:
                            data = fp.read(16 * 4096)
                            if not data:
                                break
                            s256.update(data)

                    renderctx["sha256"] = s256.hexdigest()
                    self._logger.debug("Existing {filename} checksum {s}".format(s=s256.hexdigest(), **install))
                else:
                    renderctx["sha256"] = None

                try:
                    if renderctx["sha256"] not in install["sha256"]:
                        # TODO: customise exception type
                        raise VMCTemplateChecksumError("unacceptable sha256")
                except KeyError:
                    pass

                try:
                    rendered = makot.render(**renderctx)
                except VMCPhaseError:
                    return

                try:
                    # Create the installation path if it isn't already present
                    insdir = os.path.join(os.sep, *install["dest"].split(os.sep)[:-1])
                    self._logger.debug("Creating {insdir} if necessary".format(insdir=insdir))
                    os.makedirs(insdir)
                except FileExistsError:
                    pass

                with open(install["dest"], "wb") as tplout:
                    tplout.write(rendered.encode("utf-8"))
