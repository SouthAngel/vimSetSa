" Ycm complete package
let s:cpath=expand("<sfile>:h")
let g:ycm_global_ycm_extra_conf = s:cpath.'/global_extra_conf.py'
unlet s:cpath

" Quick insert config file
let g:quickInsertSampleFile="/home/code-l/vimfiles/Userset.vim/ftplugin/python/quickInsert/quickInsertFile.cof"

" Python map
noremap <buffer> ^ :call textFunLib#ToggledWith("\#\ ")<CR>
noremap <buffer> <F5> :w<CR>:!python %<CR>
noremap <buffer> <F4> :call textFunLib#completeClass()<CR>
noremap <buffer> <leader>tt :call textFunLib#quickInsert()<CR>
noremap <buffer> <leader>tc :call textFunLib#completeClass()<CR>
