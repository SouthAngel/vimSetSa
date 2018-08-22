if exists("*initSetPythonEnv#PythonInit")
 	finish
en
let s:cpath=expand("<sfile>:h")
fun! initSetPythonEnv#PythonInit()
python3 << EOF
import sys
import re
import vim

cpath = vim.eval("s:cpath")
cpath = re.sub('[^/]+$', 'python', cpath)
if cpath not in sys.path:
	sys.path.insert(0, cpath)
del cpath
EOF

endf

