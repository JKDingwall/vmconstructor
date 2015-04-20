<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces.d/eth0"
%></%def>\
allow-ovs-dmukcomm eth0
iface eth0 inet manual

iface eth0 inet6 manual
