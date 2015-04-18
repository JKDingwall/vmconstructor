<%def name="install(i)"><%
    i["filename"] = "/etc/fstab"
%></%def>\
<%
    import os
    import vmconstruct.helpers

    fstab = os.path.join(rootpath, "etc", "fstab")
    mounts = [
        ["tmpfs", "/var/lib/openvswitch", "tmpfs", "noatime,nodev,nosuid,size=64m,mode=755", "0", "0"]
    ]

    # If the fstab has the default content then truncate it
    if sha256 == "a6b093c9916c6c54e5d634d3689f1a0132e14cce0b8e50ff445da8e85acfbd17":
        with open(fstab, "wb") as fp:
            fp.truncate()         
%>\
${vmconstruct.helpers.fstab(fstab, mounts)}
