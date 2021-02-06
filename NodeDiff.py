#!/usr/bin/python
# -*- coding: UTF-8 -*-

class NodeDiff:

    def __init__(self, nodeid: str, dingding: str, mail: str):
        self.id = nodeid
        self.dingding = dingding
        self.mail = mail
        self.rank_diff = 0
        self.shares_diff = 0
        self.status = 0
