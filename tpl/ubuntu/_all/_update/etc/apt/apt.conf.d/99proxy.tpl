<%def name="install(i)"><%
    i["filename"] = "/etc/apt/apt.conf.d/99proxy"
%></%def>\
<%
    try:
        proxy = ymlcfg["ubuntu"].get("proxy", None)
    except KeyError:
        proxy = None
%>\
# James Dingwall
# Use this proxy for apt commands
%if proxy:
Acquire::http::Proxy "${proxy}";
%else:
#Acquire::http::Proxy "http://proxy.example.com:3128";
%endif
