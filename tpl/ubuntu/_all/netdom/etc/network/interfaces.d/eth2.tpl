<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces.d/eth2"
%></%def>\
allow-ovs-dmukcomm eth2
iface eth2 inet manual

iface eth2 inet6 manual
