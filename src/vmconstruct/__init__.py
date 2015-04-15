# -*- coding: utf-8 -*-
"""\

.. module:: vmconstruct
    :platform: Unix
    :synopsis: The core vmconstruct module

.. moduleauthor:: James Dingwall <james@dingwall.me.uk>

"""

__all__ = []

__all__.append("bootstrap")
__all__.append("btrfs")

__version__ = "0.0"

import argparse
import logging
import os
import subprocess
import yaml

from . import bootstrap
from . import btrfs
from .silly import cowstatus


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
    mainap.add_argument("-q", "--quick", metavar="QUICK_BOOTSTRAP", help="quick bootstrap",
        action="store_const", dest="quick", const=True, default=False)
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
        with open(cmdline.config, "rb") as ymlcfgfp:
            ymlcfg = yaml.load(ymlcfgfp)
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

            proxy = ymlcfg[dist].get("proxy", None)

            for rel in rels:
                cowstatus("bootstrap ubuntu {r}".format(r=rel))
                relvol = distvol.create(rel)
                base = bootstrap.debootstrap(relvol.create("_bootstrap"))
                base.bootstrap(rel, archive=archive, proxy=proxy)

                cowstatus("update ubuntu {r}".format(r=rel))
                update = base.clone("_update")
                updvmyml = {
                    "dist": dist,
                    "release": rel
                }

                tpldirs = []
                tpldirs.extend([os.path.join(basetpl, dist, "_all", "_all") for basetpl in ymlcfg["build"]["basetemplates"]])
                tpldirs.extend([os.path.join(basetpl, dist, "_all", "_update") for basetpl in ymlcfg["build"]["basetemplates"]])
                tpldirs.extend([os.path.join(basetpl, dist, rel, "_all") for basetpl in ymlcfg["build"]["basetemplates"]])
                tpldirs.extend([os.path.join(basetpl, dist, rel, "_update") for basetpl in ymlcfg["build"]["basetemplates"]])

                payloads = []
                try:
                    if isinstance(ymlcfg["build"]["updates"][dist]["_all"]["payloads"], list):
                        payloads += ymlcfg["build"]["updates"][dist]["_all"]["payloads"]
                except KeyError:
                    pass

                try:
                    if isinstance(ymlcfg["build"]["updates"][dist][rel]["payloads"], list):
                        payloads += ymlcfg["build"]["updates"][dist][rel]["payloads"]
                except KeyError:
                    pass

                with update.applytemplates(ymlcfg, updvmyml, *tpldirs), update.applypayloads(*payloads):
                    if not cmdline.quick:
                        update.update(proxy=proxy)
                    try:
                        if isinstance(ymlcfg["build"]["updates"][dist]["_all"]["packages"], list):
                            [update.install(pkg) for pkg in ymlcfg["build"]["updates"][dist]["_all"]["packages"]]
                    except KeyError:

                        pass

                    try:
                        if isinstance(ymlcfg["build"]["updates"][dist][rel]["packages"], list):
                            [update.install(pkg) for pkg in ymlcfg["build"]["updates"][dist][rel]["packages"]]
                    except KeyError:
                        pass

    # create individual builds
    for vmdef in ymlcfg["build"]["vmdefs"]:
        logger.debug("Starting build of {v}".format(v=vmdef))
        cowstatus("building {v}".format(v=vmdef))
        with open(os.path.join(ymlcfg["global"]["paths"]["vmdefs"], vmdef+".yml"), "rb") as vmymlfp:
            vmyml = yaml.load(vmymlfp)

        try:
            if vmyml["settings"]["pause"] == True:
                logger.debug("Skipped build of {v} due to pause flag".format(v=vmdef))
                continue
        except KeyError:
            pass

        try:
            logger.warning("TODO: as the yaml is parsed to a json compatible structure use a json schema to validate")
            onexist = vmyml["settings"]["onexist"].lower()
        except KeyError:
            onexist = "error"

        distvol = wsroot.create(vmyml["dist"])
        relvol = distvol.create(vmyml["release"])
        base = bootstrap.ubuntu(relvol.create(vmyml.get("base", "_update")))
        try:
            vm = base.clone(vmdef)
        except FileExistsError:
            logger.warning("TODO: implement dist-upgrade, upgrade commands")
            if onexist == "rebuild":
                base._subvol._parent.create(vmdef).delete()
                vm = base.clone(vmdef)
            elif onexist in ["dist-ugrade", "upgrade"]:
                logger.warning("TODO: differentiated between dist-upgrade and upgrade")
                vm = base.open(vmdef)
                vm.update()
            elif onexist == "pass":
                continue
            else:
                raise

        # Template dirs from global template paths and vm specific
        tpldirs = []
        tpldirs.extend([os.path.join(basetpl, vmyml["dist"], "_all", "_all") for basetpl in ymlcfg["build"]["basetemplates"]])
        tpldirs.extend([os.path.join(basetpl, vmyml["dist"], "_all", vmdef) for basetpl in ymlcfg["build"]["basetemplates"]])
        tpldirs.extend([os.path.join(basetpl, vmyml["dist"], vmyml["release"], "_all") for basetpl in ymlcfg["build"]["basetemplates"]])
        tpldirs.extend([os.path.join(basetpl, vmyml["dist"], vmyml["release"], vmdef)for basetpl in ymlcfg["build"]["basetemplates"]])
        if isinstance(vmyml["settings"].get("templates", []), list):
            tpldirs.extend(vmyml["settings"].get("templates", []))

        with vm.applytemplates(ymlcfg, vmyml, *tpldirs), vm.applypayloads(*vmyml["settings"].get("payloads", [])):
            if isinstance(vmyml.get("packages", []), list):
                vm.install(*vmyml.get("packages", []))

        if isinstance(vmyml.get("disks", {}), dict):
            vm.solidify(vmyml.get("disks", {}))

    # exit
    logging.shutdown()
