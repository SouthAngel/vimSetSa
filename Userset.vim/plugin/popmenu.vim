
set mousemodel=popup
echo &term
if &term=="builtin_gui"
	echo &term
	unmenu PopUp
	nme PopUp.Copy\ all ggVG"+y
	nme PopUp.split\ V <C-W>v
	nme PopUp.split\ H <C-W>s
	nme PopUp.New :enew<CR>
	nme PopUp.Close :close<CR>
	nme PopUp.NERDTree :NERDTree<CR>
endif
