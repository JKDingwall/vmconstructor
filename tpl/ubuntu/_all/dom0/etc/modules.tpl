<%def name="install(i)"><%
    i["filename"] = "/etc/modules"
%></%def>\
<%
    import os

    # Add these modules to /etc/modules
    modules = [
        "coretemp",
        "xen-pciback"
    ]

    modsupdated = []

    with open(os.path.join(rootpath, "etc", "modules"), "rt") as fp:
        for l in fp.readlines():
            modsupdated.append(l)
            try:
                if l.strip().split() in modules:
                    modules.remove(l.split().strip())
            except IndexError:
                pass

    modsupdated += ["{m}\n".format(m=m) for m in modules]
%>\
${"".join(modsupdated)}\
