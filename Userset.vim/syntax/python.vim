
let python_highlight_all = 1
syn keyword pythonBuiltin  reversed sorted sum self
syn match pythonOper "=/|+/|-/|{/|}/|[/|]/|(/|)/|./|,"
hi link pythonOper  Operator " SpecialKey
