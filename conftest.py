# -*- coding: utf-8 -*-
"""让 pytest 能直接 import 顶层模块（pipeline / rules / ...）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
