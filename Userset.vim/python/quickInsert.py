#!/usr/bin/python
# -*- coding:utf-8 -*-

import os
import xml.etree.cElementTree as ET
import vim

def test():
    print(os.path.realpath(__file__))

def insertFromCurrentLine():
    path_file_temp = vim.vars['quickInsertSampleFile']
    expand = vim.Function("expand")
    cb = vim.current.buffer
    cw = vim.current.window
    cword = expand("<cword>").decode('utf-8')
    tree = ET.parse(path_file_temp)
    root = tree.getroot()
    content = [x.text for x in tree.iterfind('item[@word="%s"]'%cword)]
    if not content:
        return 0
    lines = content[0].splitlines()
    if not lines[0]:
        lines = [1:]
    if not lines[-1]:
        lines = [:-1]
    cb.append(content[0].splitlines(), cw.cursor[0])
    cb.append(content[0].splitlines(), cw.cursor[0])
#     vim.current.line = 'cl'

