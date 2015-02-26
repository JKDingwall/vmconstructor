"""

.. module:: vmconstruct
    :platform: Unix
    :synopsis: The core vmconstruct module

.. moduleauthor:: James Dingwall <james@dingwall.me.uk>

"""

__all__ = []

__all__.append("bootstrap")
__all__.append("btrfs")


import argparse
import logging
import os
import subprocess
import yaml

from . import bootstrap
from . import btrfs


cfgdefs = {
    "config": "vmc.yml",

    "log": "/tmp/vmc.log",
    "loglevel": "DEBUG",
    "logconfig": None
}


def main():
    """\
    The main function which will start everything up...
    """

    # Process the command line
    mainap = argparse.ArgumentParser(description="An Ubuntu virtual machine builder")
    # core options
    mainap.add_argument("-c", "--config", metavar="CONFIG FILE", help="configuration file ({d})".format(d=cfgdefs["config"]),
        action="store", dest="config", default=cfgdefs["config"])
    # logging configuration
    mainap.add_argument("-l", "--log", metavar="LOG DIRECTORY", help="path to log file ({d})".format(d=cfgdefs["log"]),
        action="store", dest="log", default=cfgdefs["log"])
    mainap.add_argument("-d", "--loglevel", metavar="LOG LEVEL", help="base logging level ({d})".format(d=cfgdefs["loglevel"]),
        action="store", dest="loglevel", default=cfgdefs["loglevel"])
    mainap.add_argument("-L", "--logconfig", metavar="LOG CONFIG", help="logging configuration file ({d})".format(d=cfgdefs["logconfig"]),
        action="store", dest="logconfig", default=cfgdefs["logconfig"])

    cmdline = mainap.parse_args()


    # Load the configuration file
    try:
        with open(cmdline.config, "rb") as fp:
            ymlcfg = yaml.load(fp)
    except Exception:
        print("error: cannot load configuration file {f}".format(f=cmdline.config))
        exit(1)


    # Set up the logger
    logger = logging.getLogger()
    logger.setLevel(cmdline.loglevel.upper())

    formatter = logging.Formatter("%(asctime)s: [%(levelname)s]%(name)s - %(message)s")
    file_log_handler = logging.FileHandler(cmdline.log)
    file_log_handler.setFormatter(formatter)
    logger.addHandler(file_log_handler)

    stderr_log_handler = logging.StreamHandler()
    stderr_log_handler.setFormatter(formatter)
    logger.addHandler(stderr_log_handler)


    # Do some prep work...
    try:
        # do I have root privileges for chroot etc
        # not checked yet

        # check we have a mount point to work on
        if not os.path.ismount(ymlcfg["workspace"]["rootpath"]):
            raise Exception("Workspace root path is not a mount point")
        logger.debug("workspace root path is on a mount point ({root})".format(root=ymlcfg["workspace"]["rootpath"]))

        # and that it is btrfs
        shellcmd = "echo -n $(df -T {root} | tail -n 1 | awk '{{print $2;}}')".format(root=ymlcfg["workspace"]["rootpath"])
        fstype = subprocess.check_output(shellcmd, shell=True).decode(encoding="UTF-8")
        if fstype != "btrfs":
            raise Exception("Workspace root is not on a btrfs filesystem ({fstype})".format(fstype=fstype))
        logger.debug("workspace filesystem is btrfs")
    except Exception:
        logger.exception("Failed to prepare environment")
        logging.shutdown()
        exit(1)


    import json
    logger.debug(json.dumps(ymlcfg, indent=2))
    #logger.debug(yaml.dump(ymlcfg))

    # do the builds
    wsroot = btrfs.subvolume(ymlcfg["workspace"]["rootpath"])
    for (dist, rels) in ymlcfg["build"]["basereleases"].items():
        distvol = wsroot.create(dist)
        if dist in ["ubuntu"]:
            try:
                archive = ymlcfg[dist]["archive"]
            except (KeyError, TypeError):
                archive = None

            for rel in rels:
                relvol = distvol.create(rel)
                base = bootstrap.debootstrap(relvol.create("_bootstrap"))
                base.bootstrap(rel, archive=archive)
                update = base.clone("_update")
                update.update()

    # create individual builds
    for vmdef in ymlcfg["build"]["vmdefs"]:
        logger.debug("Starting build of {v}".format(v=vmdef))
        with open(os.path.join(ymlcfg["global"]["paths"]["vmdefs"], vmdef+".yml"), "rb") as fp:
            vmyml = yaml.load(fp)

        distvol = wsroot.create(vmyml["dist"])
        relvol = distvol.create(vmyml["release"])
        base = bootstrap.ubuntu(relvol.create(vmyml.get("base", "_update")))
        try:
            vm = base.clone(vmdef)
        except FileExistsError:
            logger.warning("TODO: make the delete behaviour configurable")
            rebuild = True
            if rebuild:
                base._subvol._parent.create(vmdef).delete()
                vm = base.clone(vmdef)
            else:
                raise
        vm.install(*vmyml.get("packages", []))

    # exit
    logging.shutdown()
