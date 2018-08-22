import maya
maya.utils.loadStringResourcesForModule(__name__)

import sys
import os.path
import maya.cmds as cmds

MY_DROP_FUNC = 'onMayaDroppedPythonFile'

def executeDroppedPythonFile(droppedFile, obj):
    """
    Called by Maya when you Drag and Drop a Python (.py) file onto the viewport.

    Here we load the input python file and try and execute the function:
    onMayaDroppedPythonFile()

    Note: Any main code inside the Python file will also be executed, but since
          it's being imported into another module (__name__ != "__main__")

    Parameters:
        droppedFile - The Python file dropped onto the viewport
        obj - The object under the mouse

    \return True if we sucessfully called function: onMayaDroppedPythonFile()

    Example:
    - An example of a DnD Python file would be:

    MayaDropPythonTest.py:
        import maya

        def onMayaDroppedPythonFile(obj):
            print('onMayaDroppedPythonFile(' + obj + ')')
            if obj:
                maya.mel.eval('createAndAssignShader blinn ' + obj)

        if __name__ == "__main__":
            print("MayaDropPythonTest.py is being run directly")
        else:
            print("MayaDropPythonTest.py is being imported into another module")

    When we DnD this file onto an object in the viewport the output would be:
        MayaDropPythonTest.py is being imported into another module
        onMayaDroppedPythonFile(pSphere1)

    """

    ret = False

    # Add the path of the dropped file to the Python path, so we can import it.
    theDirName = os.path.dirname(droppedFile)
    theBaseName = os.path.basename(droppedFile)
    theModuleName = os.path.splitext(theBaseName)[0]

    # Add the path of the input dropped file, so we can load it.
    addedPath = False
    if theDirName not in sys.path:
        addedPath = True
        sys.path.insert(0, theDirName)

    # Try to load the module.
    loadedModule = None
    try:
        import imp
        (fp, pathname, desc) = imp.find_module(theModuleName)
        loadedModule = imp.load_module(theModuleName, fp, pathname, desc)
    finally:
        if fp:
            fp.close()

    # If we successfully loaded the module, call the dropped function.
    if loadedModule:
        if (hasattr(loadedModule, MY_DROP_FUNC)):
            ret = loadedModule.onMayaDroppedPythonFile(obj)
        else:
            str = cmds.format(maya.stringTable['y_executeDroppedPythonFile.kDropFuncMissing' ], stringArg=(theModuleName, MY_DROP_FUNC))
            cmds.warning(str)
            ret = False
    else:
        str = cmds.format(maya.stringTable['y_executeDroppedPythonFile.kLoadModuleError' ], stringArg=(theModuleName))
        cmds.warning(str)
        ret = False

    # Remove the path we added above.
    if addedPath:
        sys.path.pop(0)

    return ret
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
