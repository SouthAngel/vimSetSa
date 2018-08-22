import os
import xml.etree.cElementTree as ET

tree = ET.ElementTree(file='/home/code-l/vimfiles/Userset.vim/ftplugin/python/quickInsert/quickInsertFile.cof')
root = tree.getroot()
iter_t = tree.iterfind('item[@word="head"]')
print(iter_t)
print(dir(iter_t))
for elem in iter_t:
    print(elem.text,elem.attrib)
    print(dir(elem))

def selectNum( **args ):
    print(7646)
    return 1

