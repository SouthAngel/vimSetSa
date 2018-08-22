#!/usr/bin/python
# -*- coding:utf-8 -*-

def toLineList(content):
    return content.splitlines()

testStr = '''
    go 
    zen
'''
print(toLineList(testStr))
