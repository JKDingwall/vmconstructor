<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces.d/lo"
%></%def>\
# The loopback network interface
auto lo
iface lo inet loopback

iface lo inet6 loopback
