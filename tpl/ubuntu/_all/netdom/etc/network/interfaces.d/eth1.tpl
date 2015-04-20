<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces.d/eth1"
%></%def>\
allow-ovs-dmukcomm eth1
iface eth1 inet manual

iface eth1 inet6 manual
