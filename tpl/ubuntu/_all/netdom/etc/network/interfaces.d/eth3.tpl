<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces.d/eth3"
%></%def>\
allow-ovs-dmukcomm eth3
iface eth3 inet manual

iface eth3 inet6 manual
