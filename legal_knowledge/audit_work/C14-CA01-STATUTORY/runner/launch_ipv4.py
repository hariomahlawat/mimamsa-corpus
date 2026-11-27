"""Process-local IPv4 launch for the commissioned HF preservation runner."""
from __future__ import annotations
import os
import runpy
import socket
import sys
from pathlib import Path


def launch(arguments):
    runner = Path(__file__).resolve().with_name('corpus_runner.py')
    old_resolver = socket.getaddrinfo
    old_argv = sys.argv
    old_xet = os.environ.get('HF_HUB_DISABLE_XET')

    def ipv4(host, port, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_UNSPEC:
            family = socket.AF_INET
        return old_resolver(host, port, family, type, proto, flags)

    try:
        socket.getaddrinfo = ipv4
        os.environ['HF_HUB_DISABLE_XET'] = '1'
        sys.argv = [str(runner), *arguments]
        runpy.run_path(str(runner), run_name='__main__')
    finally:
        socket.getaddrinfo = old_resolver
        sys.argv = old_argv
        if old_xet is None:
            os.environ.pop('HF_HUB_DISABLE_XET', None)
        else:
            os.environ['HF_HUB_DISABLE_XET'] = old_xet


if __name__ == '__main__':
    launch(sys.argv[1:])
