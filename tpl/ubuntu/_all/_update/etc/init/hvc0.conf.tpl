<%def name="install(i)"><%
    i["filename"] = "/etc/init/hvc0.conf"
%></%def>\
<%
    import os

    with open(os.path.join(rootpath, "etc", "init", "tty1.conf"), "rt") as fp:
        hvc0 = fp.read().replace("tty1", "hvc0")
%>\
${hvc0}
