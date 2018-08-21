##
# Misc. Python-Mel interop. utilities
#

def createMelWrapper(fn, types = [], retType='void', ignoreDefaultArgs=True, returnCmd=False, outDir=None):
    r""" 
    \brief Create a wrapper mel proc for a python function
    
    When the mel proc is invoked, it will call the python function, 
    passing any arguments it receives, and then return the function's
    result.

    Example:
        - I need a mel proc with signature: proc string[] fn(int $a, string $b)
        - I've created a python function to do the work in 'mymod.py' which looks like:
        - def fn(a,b): return [b]*a
        python>> import mymod
        python>> maya.mel.createMelWrapper(mymod.fn,types=['int','string'], retType='string[]')
        # Result: /users/username/maya/scripts/fn.mel # 
        mel>> rehash;
        mel>> string $as[] = fn(3,"a");
        // Result: a a a // 

    \param fn the function to wrap, must be a function.
    \param types string list of mel argument types to use, 
    defaults to all 'string'.
    \param retType mel return type of the function, must be convertible to
    what fn actually returns. None means return type is 'void'.
    \param ignoreDefaultArgs  True means arguments with default values will be
    ignored when creating the mel wrapper proc.
    \param returnCmd True means return the generated mel code that defines the 
    wrapper proc, False means write it to a mel file.
    \param outDir The directory to write the generated file to.  None means 
    prompt for the directory.
    \return path to generated mel proc OR generated mel code, depending on
    returnCmd.
    """
    import maya.mel as mel
    import maya.cmds as cmds
    import os
    import inspect

    assert(inspect.isfunction(fn))
    argsp = inspect.getargspec(fn)
    args = argsp.args
    if ignoreDefaultArgs and argsp.defaults is not None:
            # remove args with default values
            args = args[0: -len(argsp.defaults)]

    if len(types) == 0:
            types = ['string' for a in args]
    paramList = ''
    argListStr = ''
    for arg,typ in zip(args,types):
            paramList += '%s $%s,'%(typ,arg)
            if typ == 'string':
                    argListStr += '"\\"" + $%s + "\\"" + "," + '%arg
            else:
                    argListStr += '$%s + "," + '%arg
    paramList = paramList[0:-1]
    argListStr = "( " + argListStr[0:-9] + " )"

    if retType == 'void': 
            retType = ''

    if fn.__module__ == '__main__':
        cmds.warning("This function does not belong to a module, it must exist in the global namespace when the mel wrapper is invoked.")
        importStatement = None
    else:
        importStatement = 'python("from %s import %s");'%(fn.__module__,fn.func_name)

    proto = 'global proc %s %s (%s) {'%(retType,fn.func_name,paramList)
    if len(args) == 0:
        tmpDecl = ""
        pyCall = 'python("%s()")'%(fn.func_name)
    else:
        tmpDecl = "string $tmp = " + argListStr + "; "
        pyCall = 'python(("%s(" + $tmp + ")"))'%(fn.func_name)

    if retType == '':
            body = pyCall + '; }'
    else:
            body = 'return `' + pyCall + '`;\n}'
    cmd = '\n    '.join([s for s in [proto,importStatement,tmpDecl,body] if s is not None])
    if returnCmd:
            return cmd
    else:
        fName = '%s.mel'%fn.func_name
        if outDir is None:
            fDir = cmds.fileDialog2(fileMode=2, 
                                    caption='Choose a directory to save %s to'%fName)
            if fDir and len(fDir) > 0:
                outDir = fDir[0]
        pth = os.path.join(outDir, fName)
        # confirm overwrite
        if os.path.exists(pth):
            yesStr,noStr = 'Yes','No'
            if cmds.confirmDialog(title='Confirm',
                                  message='Overwrite %s?'%pth,
                                  button=[yesStr,noStr],
                                  defaultButton=noStr,
                                  cancelButton=noStr,
                                  dismissString=noStr) == noStr:
                return None
        open(pth, 'w').write(cmd)
        return pth
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
