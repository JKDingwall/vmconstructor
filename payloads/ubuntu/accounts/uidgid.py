#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\
The Debian base-passwd package manages uid/gid 0-99 inclusive.  However
to make uids/gids consistent between vm builds we will merge preferred
accounts ahead of time.
"""

# TODO: supplementary groups

import argparse
import logging
import os
import time


def domerge():
    """\
    This method will merge additional entries to /etc/passwd and /etc/group
    from a list of reference ids.  (e.g. a passwd/group file from a previous
    build.  Home directories will be created where necessary but it is
    assumed that generally there is no need to copy /etc/skel for system
    accounts.
    """
    for (idfile, shadow) in [("passwd", "shadow"), ("group", "gshadow")]:
        # learn about any existing ids
        pairs = []
        try:
            with open(os.path.join(os.sep, "etc", idfile), "rt") as idfp:
                for line in idfp.read().splitlines():
                    pairs.append((line.split(":")[0], int(line.split(":")[2])))
        except (IOError, FileNotFoundError):
            # should be errno 2, no such file or directory
            # depending on what stage of the boot strap we are in
            # may affect whether the real files exist in /etc.
            pass

        names = [p[0] for p in pairs]
        ids = [p[1] for p in pairs]

        # learn about any reference accounts
        try:
            with open("{i}-reference".format(i=idfile), "rt") as idfp:
                rdata = idfp.read().splitlines()
        except (IOError, FileNotFoundError):
            try:
                with open(os.path.join("/etc/vmconstruct/{i}-reference".format(i=idfile), idfile), "rt") as idfp:
                    rdata = idfp.read().splitlines()
            except (IOError, FileNotFoundError):
                logging.debug("No reference account information found for {f}".format(f=idfile))
                rdata = []

        # merge reference ids
        merged_users = []
        with open(os.path.join(os.sep, "etc", idfile), "ab") as idfp:
            print(os.path.join(os.sep, "etc", idfile))
            with open(os.path.join(os.sep, "etc", shadow), "ab") as shfp:
                for ref in rdata:
                    if int(ref.split(":")[2]) < 100:
                        # A managed id, ignore it
                        # TODO: if group and merged user update supplementary groups if necessary
                        logging.debug("{u} ({i}) is a managed id in {f}, ignoring".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                        continue

                    if int(ref.split(":")[2]) in ids or ref.split(":")[0] in names:
                        if (ref.split(":")[0], int(ref.split(":")[2])) not in pairs:
                            raise Exception("{u} ({i}) is conflicting in {f}".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                        else:
                            # this is already known
                            logging.debug("{u} ({i}) is already known in {f}, ignoring".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                            continue

                    logging.info("Generating {f} entry for {u} ({i}) from reference data".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                    # write in the account detail
                    idfp.write(ref.encode("utf-8"))
                    idfp.write("\n".encode("utf-8"))

                    # make up a shadow entry
                    if idfile == "passwd":
                        merged_users.append(ref.split(":")[0])
                        shfp.write("{u}:*:{today}:0:99999:7:::\n".format(u=ref.split(":")[0], today=int(time.time() / (24*60*60))).encode("utf-8"))
                        # and create a home directory if one doesn't exist
                        pathfilter = ["/var/run"]
                        if not os.path.exists(os.path.join(os.sep, ref.split(":")[5][1:])) and not [x for x in pathfilter if ref.split(":")[5].startswith(x)]:
                            logging.info("Created home directory {h} for {u} ({i}) from reference data".format(h=ref.split(":")[5], u=ref.split(":")[0], i=ref.split(":")[2]))
                            os.makedirs(os.path.join(os.sep, ref.split(":")[5][1:]))
                            os.chown(os.path.join(os.sep, ref.split(":")[5][1:]), int(ref.split(":")[2]), int(ref.split(":")[3]))
                            #need to copy /etc/skel?
                    elif idfile == "group":
                        shfp.write("{g}:*::\n".format(g=ref.split(":")[0]).encode("utf-8"))


if __name__ == "__main__":
    """\
    Perform setup and then do the necessary work.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    domerge()
