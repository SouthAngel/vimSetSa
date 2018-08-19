if exists("*textFunLib#ToggledWith")
	finish
en

fu! textFunLib#ToggledWith(head) range
	let a:bpos = a:firstline
	let a:epos = a:lastline
	let a:cpos=a:bpos
	if match(getline(a:bpos), a:head)
		let a:pat = "^"
		let a:sub = a:head
	else
		let a:pat = a:head
		let a:sub = ""
	en
	wh a:cpos <= a:epos
	    let a:old = getline(a:cpos)
	    let a:new = substitute(a:old, a:pat, a:sub, "")
	    call setline(a:cpos, a:new)
	    let a:cpos += 1
	endw
	unl a:old
	unl a:new
	unl a:bpos
	unl a:epos
	unl a:cpos
	unl a:pat
	unl a:sub
endf


