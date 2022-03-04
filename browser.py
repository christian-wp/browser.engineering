import gzip
import socket
import ssl
import sys
import urllib.parse

view_source = False

def add_headers(headers):
    headers.append("\r\n")
    joined = "\r\n".join(headers)
    return bytes(joined, encoding="utf8")

def response_headers(response):
    headers = {}
    while True:
        line = str(response.readline(), encoding="utf-8")
        if line == "\r\n": break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers

def read_chunks(response):
    body = ""
    while True:
        chunk_size = response.readline().split(b"\r\n")[0]
        if not chunk_size: break
        body += str(gzip.decompress(response.read(int(chunk_size, 16))), encoding="utf-8")
    return body

def response_body(response, headers):
    if headers.get("transfer-encoding") == "chunked":
        return read_chunks(response)
    return str(gzip.decompress(response.read()), encoding="utf-8")

def request(url):

    if not url:
        with open("home.html") as f:
            return {}, f.read()

    scheme, url = url.split(":", 1)

    if scheme == "data":
        mediatype, data = url.split(',', 1)
        return {}, data

    if scheme == "view-source":
        global view_source
        view_source = True
        scheme, url = url.split(":", 1)

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
        "User-Agent: BE/0.0",
        "Accept-Encoding: gzip"
    ]))
    response = s.makefile("rb", newline=b"\r\n")
    statusline = str(response.readline(), encoding="utf-8")
    version, status, explanation = statusline.split(" ", 2)
    if status == "301":
        return request(response_headers(response)["location"])
    assert status == "200", "{}: {}".format(status, explanation)

    headers = response_headers(response)
    body = response_body(response, headers)
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

def transform(body):
    global view_source
    if not view_source: return body
    b = ""
    for c in body:
        if c == "<":
            b += "&lt;"
        elif c == ">":
            b += "&gt;"
        else:
            b += c
    return b

def load(url):
    headers, body = request(url)
    show(transform(body))

if __name__ == "__main__":
    url = ""
    if 1 < len(sys.argv):
        url = sys.argv[1]
    load(url)
