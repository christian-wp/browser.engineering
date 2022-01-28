import socket
import ssl
import sys
import urllib.parse

def add_headers(headers):
    headers.append("\r\n")
    joined = "\r\n".join(headers)
    return bytes(joined, encoding="utf8")

def request(url):

    scheme, url = url.split(":", 1)

    if scheme == "data":
        mediatype, data = url.split(',', 1)
        return {}, data

    _, authority, url = url.split("/", 2)

    if scheme == "file":
        with open(url) as f:
            return {}, f.read()

    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)
    host, path = url.split("/", 1)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)
    else:
        port = 80 if scheme == "http" else 443

    path = "/" + path
    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    s.connect((host, port))

    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    s.send(add_headers([
        "GET {} HTTP/1.1".format(path),
        "Host: {}".format(host),
        "Connection: close",
        "User-Agent: BE/0.0"
    ]))
    response = s.makefile("r", encoding="utf8", newline="\r\n")
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)
    headers = {}
    
    while True:
        line = response.readline()
        if line == "\r\n": break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    body = response.read()
    s.close()
    return headers, body

def show(body):
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            print(c, end="")

def load(url):
    headers, body = request(url)
    show(body)

if __name__ == "__main__":
    load(sys.argv[1])
