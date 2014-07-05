__all__ = []

import errno
import logging
import os
import subprocess


class subvolume(object):
    def __init__(self, path, parent=None):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._path = path
        self._parent = parent

        self._logger.debug("Initialised for path {p}".format(p=path))


    def __eq__(self, other):
        if isinstance(other, subvolume):
           other = other.path

        self._logger.debug("Comparing {x} to {y}".format(x=other, y=self.path))

        return(other == self.path)


    def __str__(self):
        return("{m}.{n}: {p}".format(m=self.__class__.__module__, n=self.__class__.__name__, p=self._path))


    @property
    def path(self):
        return(self._path)


    def create(self, name, eexist=False):
        """
        Create a subvolume under this volume
        """

        # This could include a check for os.sep in name and recursively create subvols
        # as required.

        if eexist and os.path.join(self._path, name) in self.list():
            # An existing subvolume of this name and we asked for it to raise an error
            raise OSError(errno.EEXIST, os.path.join(self._path, name))

        if not os.path.join(self._path, name) in self.list():
            if os.path.exists(os.path.join(self._path, name)):
                # There is already a dirent of name in the path and it is not a subvolume
                raise OSError(errno.EEXIST, os.path.join(self._path, name))
            else:
                cmd  = ["btrfs", "subvolume", "create", os.path.join(self._path, name)]
                self._logger.debug("Creating subvolume with command: {cmd}".format(cmd=cmd))
                subprocess.check_output(cmd)

        return(subvolume(os.path.join(self._path, name), self))


    def list(self):
        """
        List existing subvolumes in this subvolume
        """
        subvols = []
        cmd = ["btrfs", "subvolume", "list", self._path]
        for subvol in subprocess.check_output(cmd).decode(encoding="UTF-8").splitlines():
            subvols.append(subvolume(os.path.join(self._path, subvol.split().pop())))

        return(subvols)


    def delete(self, recursive=False):
        """
        Delete a subvolume (recursively)
        """

        if recursive:
            for subvol in self.list():
                subvol.delete(recursive)

        cmd = ["btrfs", "subvolume", "delete", self._path]
        self._logger.debug("Deleting subvolume with command: {cmd}".format(cmd=cmd))
