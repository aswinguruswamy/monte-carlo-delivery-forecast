"""Shared test setup.

AC4 (MCF-10) and CLAUDE.md: tests never use the network. Any attempt to open
a network connection in a test fails at once. (Subprocesses such as git are
separate processes and are not affected.)
"""

import socket

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise RuntimeError("tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
