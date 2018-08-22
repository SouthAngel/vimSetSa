#!/usr/bin/python
# -*- coding:utf-8 -*-

import os, re, time
from datetime import datetime
import xml.etree.cElementTree as ET
import vim


# Templete insert
def insertFromCurrentLine():
    path_file_temp = vim.vars['quickInsertSampleFile']
    expand = vim.Function("expand")
    cb = vim.current.buffer
    cw = vim.current.window
    cword = expand("<cword>").decode('utf-8')
    tree = ET.parse(path_file_temp)
    root = tree.getroot()
    content = [x.text for x in tree.iterfind('content/item[@word="%s"]'%cword)]
    if not content:
        return 0
    lines = SubData(content[0], path_file_temp).run().splitlines()
    if not lines[0].strip():
        lines.pop(0)
    if not lines[-1].strip():
        lines.pop(len(lines)-1)
    row_num = cw.cursor[0]
    vim.current.line = lines[0]
    if len(lines) > 1:
        cb.append(lines[1:], row_num)


class SubData(object):
    KEY_TIME = '%time%'
    Format_Time = ''

    def __init__(self, input_, sampleFile):
        self.input = input_
        self.output = input_
        self.tree = ET.parse(sampleFile)
        self.sample()

    def __str__(self):
        return self.output

    def run(self):
        self.subTime()
        self.subOther()
        return self.output

    def findName(self, patten):
        return [x.text for x in self.tree.iterfind(patten)]

    def sample(self):
        content = self.findName('sample/timeFormat')
        if content:
            self.Format_Time = content[0]

    def subTime(self):
        str_time = time.strftime(self.Format_Time, time.localtime())
        self.output = self.output.replace(self.KEY_TIME, str_time)


    def subOther(self):
        values = re.findall('%.*%', self.output)
        for key in values:
            content = self.findName('sample/item[@word="%s"]'%key[1:-1])
            if content:
                self.output = self.output.replace(key, content[0])


# Class complete
def completeClass():
    cb = vim.current.buffer
    cw = vim.current.window
    input_type = vim.current.line
    split_first = input_type.split('  ')
    if not split_first:
        return 0
    name_class = split_first[0] 
    list_attr = []
    if len(split_first) > 1:
        list_attr = split_first[1].split(' ')
    list_lines = [
            'class %s(object):'%name_class, 
            '', 
            '    def __init__(self):', 
            '        super(%s, self).__init__()'%name_class
            ]
    for i in list_attr:
        list_lines.append('')
        list_lines.append('    def %s(self):'%i)
        list_lines.append('        print(\'%s\')'%i)
    vim.current.line = list_lines[0]
    cb.append(list_lines[1:], cw.cursor[0])
