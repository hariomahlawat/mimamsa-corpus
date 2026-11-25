"""Sandboxed child: parse one PDF with pypdfium2 and print JSON. Test modes simulate hostile inputs."""
import json
import os
import socket
import sys
import time

path, mode = sys.argv[1], sys.argv[2]
info = {"uid": os.getuid()}
try:
    socket.create_connection(("1.1.1.1", 443), timeout=1).close()
    info["network"] = "reachable"
except OSError as e:
    info["network"] = f"blocked ({type(e).__name__})"
try:
    open("/etc/shadow").read(1); info["read_etc_shadow"] = "ALLOWED"
except OSError:
    info["read_etc_shadow"] = "denied"

if mode == "memory_bomb":
    blocks = []
    while True:
        blocks.append(bytearray(64 * 2**20))
elif mode == "hang":
    while True:
        time.sleep(1)
elif mode == "cpu_spin":
    while True:
        pass

import pypdfium2 as pdfium  # noqa: E402

doc = pdfium.PdfDocument(path)
pages = []
for i in range(len(doc)):
    tp = doc[i].get_textpage()
    pages.append(len(tp.get_text_range()))
print(json.dumps({"pages": len(doc), "chars_per_page": pages[:50], "sandbox": info}))
