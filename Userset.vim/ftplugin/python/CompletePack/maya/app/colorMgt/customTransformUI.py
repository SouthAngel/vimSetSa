"""
Color management UI code.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
from functools import partial

def dialogFactory(type):
    if type == 'rendering space':
        return RenderingSpaceDialog()
    elif type == 'view':
        return ViewTransformDialog()
    elif type == 'input':
        return InputTransformDialog()
    elif type == 'output':
        return OutputTransformDialog()
    elif type == 'playblastOutput':
        return PlayblastOutputTransformDialog()
    else:
        errorStr = maya.stringTable['y_customTransformUI.kColorMgtBadCustomType' ] % type
        raise RuntimeError(errorStr)

def addCustomTransformDialog(type):
    """Add and return a user transform.

    Return transform name, or empty string in case of error or cancel."""

    done = False
    name = ''

    while not done:
        dialog = dialogFactory(type)
        dialogRetVal = ''
        try:
            dialogRetVal = dialog.show()
        except RuntimeError, ex:
            # In case of error (e.g. bad input), loop and show dialog again.
            pass
            
        if len(dialogRetVal) > 0:
            done = True
            if dialogRetVal == 'save':
                okStr = maya.stringTable['y_customTransformUI.kColorMgtOK' ]
                try:
                    dialog.add()
                except RuntimeError, ex:
                    # Return error: add didn't pan out, so don't try applying.  
                    titleStr = maya.stringTable['y_customTransformUI.kColorMgtAddTransformFailed' ]
                    buttonStr = okStr
                    cmds.confirmDialog(
                        title=titleStr, message=unicode(ex), button=buttonStr, icon='warning')
                    return ''

                name = dialog.name

                try:
                    dialog.apply()
                except RuntimeError, ex:
                    # In case of error on apply, remove the transform.
                    titleStr = maya.stringTable['y_customTransformUI.kColorMgtBadTransform' ]
                    buttonStr = okStr
                    cmds.confirmDialog(
                        title=titleStr, message=unicode(ex), button=buttonStr, icon='warning')
                    dialog.remove()
                    name = ''

    return name if dialogRetVal == 'save' else ''

class Dialog(object):

    _dirSrc = maya.stringTable['y_customTransformUI.kColorMgtDirSrc' ]
    _dirDst = maya.stringTable['y_customTransformUI.kColorMgtDirDst' ]
    _extensions = cmds.colorManagementCatalog(listSupportedExtensions=True)
        

    def __init__(self, path='', name='', transformConnection=''):

        self.path = path
        self.name = name
        self.transformConnection = transformConnection
        self._pathWidget = None
        self._nameWidget = None
        self._transformConnectionWidget = None

    def show(self):

        titleString = maya.stringTable['y_customTransformUI.kColorMgtCustomTransformUI' ] % self.title()

        return cmds.layoutDialog(ui=self.build, title=titleString)

    def build(self):

	# Get the layoutDialog's formLayout.
	#
	form = cmds.setParent(q=True)

	# layoutDialog's are unfortunately not resizable, so hard code a size
        # here, to make sure all UI elements are visible.
	#
	cmds.formLayout(form, e=True, width=500)

        self._pathWidget = cmds.textFieldGrp(
            ad2=2,
            label=maya.stringTable['y_customTransformUI.kColorMgtCustomTransformFilePath'],
            text=self.path)

        browseIcon = cmds.symbolButton(
            image="navButtonBrowse.png", command=self.onPathBrowse)

        self._nameWidget = cmds.textFieldGrp(
            ad2=2, label=maya.stringTable['y_customTransformUI.kColorMgtCustomTransformName'],
            text=self.name)

        transformConnectionLabel = maya.stringTable['y_customTransformUI.kColorMgtTransformConnection' ]\
                          % self.direction()
        self._transformConnectionWidget = cmds.optionMenuGrp(
            ad2=2, label=transformConnectionLabel)

        transformConnections = cmds.colorManagementCatalog(
            listTransformConnections=True, type=self.type())
        for transformConnection in transformConnections:
            cmds.menuItem(label=transformConnection)
        cmds.setParent('..', menu=True)

        saveBtn = cmds.button(label=maya.stringTable['y_customTransformUI.kSave' ],
                              command=partial(self.onDismissButton, msg='save'))

        cancelBtn = cmds.button(label=maya.stringTable['y_customTransformUI.kCancel' ],
                              command=partial(self.onDismissButton, msg='cancel'))

        vSpc = 10
        hSpc = 10
        rSpc = 50

        cmds.formLayout(
            form, edit=True,
            attachForm=[(self._pathWidget,                'top',    vSpc),
                        (self._pathWidget,                'left',   0),
                        (browseIcon,                      'top',    vSpc),
                        (browseIcon,                      'right',  0),
                        (self._nameWidget,                'left',   0),
                        (self._nameWidget,                'right',  rSpc),
                        (self._transformConnectionWidget, 'left',   0),
                        (self._transformConnectionWidget, 'right',  rSpc),
                        (saveBtn,                         'bottom', vSpc),
                        (cancelBtn,                       'bottom', vSpc),
                        (cancelBtn,                       'right',  hSpc)],
            attachControl=[
                (self._pathWidget, 'right', 0, browseIcon),
                (self._nameWidget, 'top', vSpc, self._pathWidget),
                (self._transformConnectionWidget, 'top', vSpc, self._nameWidget),
                (saveBtn,       'top',   vSpc, self._transformConnectionWidget),
                (cancelBtn,     'top',   vSpc, self._transformConnectionWidget),
                (saveBtn,       'right', hSpc, cancelBtn)])

    def onPathBrowse(self, data):
        # No documentation for symbolButton command script argument in
        # Python, but it is of type boolean, and Python complains of
        # missing argument if omitted.

        multiFilter = maya.stringTable['y_customTransformUI.kTransformFiles' ]
        multiFilter += ' ('
        for extension in Dialog._extensions:
            multiFilter += ' *.' + extension
        multiFilter += ')'

        selectedPath = cmds.fileDialog2(fileMode=1, fileFilter=multiFilter)

        if selectedPath is not None and len(selectedPath[0]) > 0:
            cmds.textFieldGrp(self._pathWidget, edit=True, text=selectedPath[0])

    def onDismissButton(self, data, msg):
        # Same comment for data argument as for onPathBrowse() method.

        # Copy widget data.
        self.path = cmds.textFieldGrp(self._pathWidget, query=True, text=True)
        self.name = cmds.textFieldGrp(self._nameWidget, query=True, text=True)
        self.transformConnection = cmds.optionMenuGrp(self._transformConnectionWidget, query=True,
                                             value=True)

        cmds.layoutDialog(dismiss=msg)

    def add(self):
        """Add the transform to the catalog."""
        cmds.colorManagementCatalog(
            addTransform=self.name, type=self.type(), path=self.path,
            transformConnection=self.transformConnection)

    def remove(self):
        """Remove the transform from the catalog."""
        cmds.colorManagementCatalog(removeTransform=self.name, type=self.type())

class RenderingSpaceDialog(Dialog):

    def __init__(self, path='', name='', transformConnection=''):
        super(RenderingSpaceDialog, self).__init__(
            path=path, name=name, transformConnection=transformConnection)

    def type(self):
        return 'rendering space'

    def direction(self):
        return Dialog._dirDst

    def title(self):
        return maya.stringTable['y_customTransformUI.kColorMgtCustomRenderingSpace' ],

    def apply(self):
        cmds.colorManagementPrefs(edit=True, renderingSpaceName=self.name)

class ViewTransformDialog(Dialog):

    def __init__(self, path='', name='', transformConnection=''):
        super(ViewTransformDialog, self).__init__(
            path=path, name=name, transformConnection=transformConnection)

    def type(self):
        return 'view'

    def direction(self):
        return Dialog._dirSrc

    def title(self):
        return maya.stringTable['y_customTransformUI.kColorMgtCustomView' ],

    def apply(self):
        cmds.colorManagementPrefs(edit=True, viewTransformName=self.name)

class InputTransformDialog(Dialog):

    def __init__(self, path='', name='', transformConnection=''):
        super(InputTransformDialog, self).__init__(
            path=path, name=name, transformConnection=transformConnection)

    def type(self):
        return 'input'

    def direction(self):
        return Dialog._dirDst

    def title(self):
        return maya.stringTable['y_customTransformUI.kColorMgtCustomInput' ],

    def apply(self):
        # An added input space cannot be applied immediately; it will be
        # applied by an image node that will use it.
        pass

class OutputTransformDialog(Dialog):

    def __init__(self, path='', name='', transformConnection=''):
        super(OutputTransformDialog, self).__init__(
            path=path, name=name, transformConnection=transformConnection)

    def type(self):
        return 'output'

    def direction(self):
        return Dialog._dirSrc

    def title(self):
        return maya.stringTable['y_customTransformUI.kColorMgtCustomOutput' ],

    def apply(self):
        cmds.colorManagementPrefs(edit=True, outputTransformName=self.name, outputTarget='renderer')

class PlayblastOutputTransformDialog(Dialog):
    def __init__(self, path='', name='', transformConnection=''):
        super(PlayblastOutputTransformDialog, self).__init__(
            path=path, name=name, transformConnection=transformConnection)

    def type(self):
        return 'playblastOutput'

    def direction(self):
        return Dialog._dirSrc

    def title(self):
        return maya.stringTable['y_customTransformUI.kColorMgtCustomPlayblastOutput' ],

    def apply(self):
        cmds.colorManagementPrefs(edit=True, outputTransformName=self.name, outputTarget='playblast')

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
