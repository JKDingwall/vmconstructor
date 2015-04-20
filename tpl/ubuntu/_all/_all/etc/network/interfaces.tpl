<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces"
%></%def>\
# interfaces(5) used by ifup(8) and ifdown(8)
# include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d
