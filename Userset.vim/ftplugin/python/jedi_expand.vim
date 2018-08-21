let s:cpath=expand("<sfile>:h")
py3 << EOF
import os
import sys
import vim

completPath = vim.eval("s:cpath") + '/CompletePack'
if completPath not in sys.path:
    sys.path.insert(0, completPath)
EOF
unlet s:cpath
