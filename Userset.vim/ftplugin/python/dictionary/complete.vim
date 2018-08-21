let s:cpath = glob("<sfile>:h/*-dict", v:true, v:true)
for each in s:cpath
	exe "set\ dictionary-=".each
	exe "set\ dictionary+=".each
endfor	
unlet each
unlet s:cpath
