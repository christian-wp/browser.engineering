import gzip
import pickle
import socket
import ssl
import sys
import time
import tkinter
import urllib.parse

WIDTH, HEIGHT = 800, 600
cache = {}
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

def parse_status_line(status_line):
    return status_line.split(" ", 2)

def expiration_time(headers):
    cache_control = headers.get("cache-control")
    if not cache_control: return None
    if max_age := cache_control.split("=")[-1]:
        return int(max_age) + int(time.time())
    return None

def cache_response(request_url, status_line, headers, body=""):
    if headers.get("cache-control") == "no-store": return
    version, status, explanation = parse_status_line(status_line)
    cache[request_url] = {
        "version": version,
        "status": status,
        "explanation": explanation,
        "headers": headers,
        "body": body,
        "expiration": expiration_time(headers)
    }

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

def check_cache(url):
    if cached_response := cache.get(url):
        expiration = cached_response.get("expiration")
        if expiration and int(time.time()) < expiration:
            return cached_response
    return None

def request(url):
    if cached_response := check_cache(url):
        status = cached_response["status"]
        if status == "301":
            print("cache 301")
            return request(cached_response["headers"].get("location"))
        elif status == "200":
            print("cache 200")
            return cached_response["headers"], cached_response["body"]

    request_url = url

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
    status_line = str(response.readline(), encoding="utf-8")
    version, status, explanation = parse_status_line(status_line)
    if status == "301":
        headers = response_headers(response)
        cache_response(request_url, status_line, headers)
        return request(headers["location"])
    assert status == "200", "{}: {}".format(status, explanation)

    headers = response_headers(response)
    body = response_body(response, headers)
    s.close()
    cache_response(request_url, status_line, headers, body)
    return headers, body

def is_html_document(body):
    doctype = "<!doctype html>"
    return body[0:len(doctype)].lower() == doctype 

def lex(body):
    entity = ""
    in_angle = False
    in_body = not is_html_document(body)
    in_entity = False
    tag = ""
    text = ""
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
                    text += c
                    entity = ""
                    in_entity = False
                elif entity == "&lt;":
                    text += "<"
                    entity = ""
                    in_entity = False
                elif entity == "&gt;":
                    text += ">"
                    entity = ""
                    in_entity = False
            else: 
                text += c
    return text

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
    text = lex(transform(body))
    #print(text)

def load_cache():
    global cache
    try:
        with open('cache.pickle', 'rb') as f:
            cache = pickle.load(f)
    except FileNotFoundError:
        dump_cache()

def dump_cache():
    global cache
    with open('cache.pickle', 'wb') as f:
        pickle.dump(cache, f, protocol=0)

if __name__ == "__main__":
    load_cache()
    url = ""
    if 1 < len(sys.argv):
        url = sys.argv[1]
    load(url)
    dump_cache()
