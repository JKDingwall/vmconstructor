#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\
The Debian base-passwd package manages uid/gid 0-99 inclusive.  However
to make uids/gids consistent between vm builds we will merge preferred
accounts ahead of time.
"""

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
        ids = []
        names = []
        try:
            # Learn the ids from the existing file
            with open(os.path.join(os.sep, "etc", idfile), "rt") as idfp:
                lines = idfp.read().splitlines()
            for line in lines:
                names.append(line.split(":")[0])
                ids.append(line.split(":")[2])
        except IOError:
            # should be errno 2, no such file or directory
            pass

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
        with open(os.path.join(os.sep, "etc", idfile), "ab") as idfp:
            with open(os.path.join(os.sep, "etc", shadow), "ab") as shfp:
                for ref in rdata:
                    if int(ref.split(":")[2]) < 100:
                        # A managed id, ignore it
                        logging.debug("{u} ({i}) is a managed id in {f}, ignoring".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                        continue

                    if int(ref.split(":")[2]) in ids or ref.split(":")[0] in names:
                        # this is already known or conflicts with an existing entry so ignore
                        logging.debug("{u} ({i}) is conflicting in {f}, ignoring".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                        continue

                    logging.debug("Generating {f} entry for {u} ({i}) from reference data".format(f=idfile, u=ref.split(":")[0], i=ref.split(":")[2]))
                    # write in the account detail
                    idfp.write(ref)
                    idfp.write("\n")

                    # make up a shadow entry
                    if idfile == "passwd":
                        shfp.write("{u}:*:{today}:0:99999:7:::\n".format(u=ref.split(":")[0], today=int(time.time() / (24*60*60))))
                        # and create a home directory if one doesn't exist
                        pathfilter = ["/var/run"]
                        if not os.path.exists(os.path.join(os.sep, ref.split(":")[5][1:])) and not [x for x in pathfilter if ref.split(":")[5].startswith(x)]:
                            logging.debug("Created home directory {h} for {u} ({i}) from reference data".format(h=ref.split(":")[5], u=ref.split(":")[0], i=ref.split(":")[2]))
                            os.makedirs(os.path.join(os.sep, ref.split(":")[5][1:]))
                            os.chown(os.path.join(os.sep, ref.split(":")[5][1:]), int(ref.split(":")[2]), int(ref.split(":")[3]))
                            #need to set permissions on the homedir too???
                    elif idfile == "group":
                        shfp.write("{g}:*::\n".format(g=ref.split(":")[0]))


if __name__ == "__main__":
    """\
    Perform setup and then do the necessary work.
    """
    logger = logging.getLogger()

    domerge()
