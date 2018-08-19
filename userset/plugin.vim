let s:plugin_path=glob(("~/vimfiles/Userset.vim/*", v:true, v:true)
for path in s:plugin_path
	exe "set\ rtp-=".path."\ rtp+=".path
endfor	
unlet s:plugin_path
