import socket
import ssl
import sys
import urllib.parse

def add_headers(headers):
    headers.append("\r\n")
    joined = "\r\n".join(headers)
    return bytes(joined, encoding="utf8")

def request(url):

    if not url:
        with open("home.html") as f:
            return {}, f.read()

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

def is_html_document(body):
    doctype = "<!doctype html>"
    return body[0:len(doctype)].lower() == doctype 

def show(body):
    entity = ""
    in_angle = False
    in_body = not is_html_document(body)
    in_entity = False
    tag = ""
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
            if tag == "body": in_body = True
            if tag == "/body": in_body = False
            tag = ""
        elif in_angle:
            tag += c
        elif in_body and not in_angle:
            if c == "&":
                in_entity = True
                entity = c
            elif in_entity:
                entity += c
                if 4 < len(entity):
                    print(c, end="")
                    entity = ""
                    in_entity = False
                elif entity == "&lt;":
                    print("<", end="")
                    entity = ""
                    in_entity = False
                elif entity == "&gt;":
                    print(">", end="")
                    entity = ""
                    in_entity = False
            else: 
                print(c, end="")

def load(url):
    headers, body = request(url)
    show(body)

if __name__ == "__main__":
    url = ""
    if 1 < len(sys.argv):
        url = sys.argv[1]
    load(url)
