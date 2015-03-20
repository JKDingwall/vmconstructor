<%def name="install(i)"><%
    i["filename"] = "/etc/hostname"
%></%def>\
<%
    try:
        hostname = vmyml["settings"].get("hostname", "ubuntu")
    except KeyError:
        hostname = "ubuntu"
%>\
${hostname}
