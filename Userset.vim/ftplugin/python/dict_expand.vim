let s:cfile=expand("<sfile>:h")
let s:dict_path=substitute(s:cfile, "ftplugin\\\\python", "dictionary", "")
exe "set\ dictionary-=".s:dict_path."\ dictionary+=".s:dict_path
exe "source\ ".s:cfile."\\dictionary\\complete.vim"
unl s:dict_path
unlet s:cfile
