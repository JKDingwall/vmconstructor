# -*- coding: utf-8 -*-
"""\

.. module:: vmconstruct.helpers
    :platform: Unix
    :synopsis: Helper functions

.. moduleauthor:: James Dingwall <james@dingwall.me.uk>

"""

__all__ = []

import logging
import tabulate


def fstab(fstab, mounts):
    import tabulate

    # Append mount to /etc/fstab if nothing already present
    headers = ["# <file system>", "<mount point>", "<type>", "<options>", "<dump>", "<pass>"]

    # Read file and learn currently configured mounts
    fmts = {}
    mnts = {}
    lno = 0
    hlno = -1
    with open(fstab, "rt") as fp:
        for line in [x.strip() for x in fp.read().splitlines()]:
            if line and line[0] != "#":
                mnts[line.split()[1]] = (lno, line.split())
            else:
                if line.split() == " ".join(headers).split():
                    hlno = lno
                fmts[lno] = line
            lno += 1

    # Insert or replace our mounts
    for mount in mounts:
        if mount[1] in mnts:
            (lno, _) = mnts.get(mount[1])
            mnts[mount[1]] = (lno, mount)
        else:
            mnts[mount[1]] = (None, mount)

    table = []
    for mount in sorted(mnts.keys()):
        table.append(mnts[mount][1])

    tabu = tabulate.tabulate(table, headers, tablefmt="plain", stralign="left", numalign="left").splitlines()
    header = tabu.pop(0)

    orderedlines = []
    if hlno == -1:
        orderedlines.append(header)
    else:
        fmts[hlno] = header

    lno = 0
    while tabu or fmts:
        if lno in fmts:
            # Insert formatting/comments etc
            orderedlines.append(fmts.pop(lno))
            lno += 1
        elif lno in [x[0] for x in mnts.values()]:
            # Insert the next mount line if it was in file originally
            # This assumes the original file was ordered by mountpoint
            orderedlines.append(tabu.pop(0))
            lno += 1
        else:
            # A new mount line
            orderedlines.append(tabu.pop(0))

    return("\n".join(orderedlines))
