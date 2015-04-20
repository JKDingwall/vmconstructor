<%def name="install(i)"><%
    i["filename"] = "/etc/default/openvswitch-switch"
    i["phase"] = ["POST"]
    i["sha256"] = [
        "f144e97bec21a1c047810af48172464d903b3c0af00a5ac92392a7b1eaa96848"
    ]
%></%def>\
<%text># This is a POSIX shell fragment                -*- sh -*-

# FORCE_COREFILES: If 'yes' then core files will be enabled.
# FORCE_COREFILES=yes

# OVS_CTL_OPTS: Extra options to pass to ovs-ctl.  This is, for example,
# a suitable place to specify --ovs-vswitchd-wrapper=valgrind.
OVS_CTL_OPTS="--delete-bridges"</%text>
