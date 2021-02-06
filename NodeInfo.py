#!/usr/bin/python
# -*- coding: UTF-8 -*-

class NodeInfo:

    def __init__(self, nodeid: str, dingding: str, mail: str):
        nodeid = nodeid.lower()
        if nodeid.startswith('0x'):
            self.id = nodeid[2:]
        else:
            self.id = nodeid
        self.dingding = dingding
        self.mail = mail
        self.rank = 0
        self.name = ""
        self.shares = 0
