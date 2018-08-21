"""
	These classes are the UI builders for the options of import and Export
	of a render setup.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds

import maya.app.renderSetup.model.jsonTranslatorUtils as jsonTranslatorUtils
import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals


# Text to localize
kNotes                  = maya.stringTable['y_importExportUI.kNotes'   ]
kPreview                = maya.stringTable['y_importExportUI.kPreview' ]
kOverwrite              = maya.stringTable['y_importExportUI.kOverwrite' ]
kOverwriteExplanation   = maya.stringTable['y_importExportUI.kOverriteExplanation' ]
kMerge                  = maya.stringTable['y_importExportUI.kMerge' ]
kMergeExplanation       = maya.stringTable['y_importExportUI.kMergeExplanation' ]
kMergeAOVExplanation    = maya.stringTable['y_importExportUI.kMergeAOVExplanation' ]
kRename                 = maya.stringTable['y_importExportUI.kRename' ]
kRenameExplanation      = maya.stringTable['y_importExportUI.kRenameExplanation' ]
kTextToPrepend          = maya.stringTable['y_importExportUI.kTextToPrepend' ]
kDefaultTextToPrepend   = 'Import_'
kGeneralOptions         = maya.stringTable['y_importExportUI.kGeneralOptions' ]

# List of all error messages
kUnknownFile = maya.stringTable['y_importExportUI.kUnknownFile' ]


class ParentGuard(object):
    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        cmds.setParent('..')

# Indentation used by the UI        
DEFAULT_UI_INDENTATION = 12


class ExportAllUI(object):
    """
        Helper class to build the Options UI for the fileDialog2 command used when exporting all
    """

    # Notes
    notesText = None
    notesTextEditor = None

    @staticmethod
    def addOptions(parent):
        cmds.setParent(parent)
        cmds.text(label=kNotes, align='left')
        ExportAllUI.notesTextEditor = \
            cmds.scrollField(text='' if not ExportAllUI.notesText else ExportAllUI.notesText,
                             numberOfLines=5, changeCommand=ExportAllUI.setNotesText, wordWrap=True)

    @staticmethod
    def setNotesText(data):
        """ 
            Preserve the notes because it's consumed after the UI is gone.
            Note: Trap the focus changed which is the only way to have the text for a scroll field.
        """
        ExportAllUI.notesText = cmds.scrollField(ExportAllUI.notesTextEditor, query=True, text=True)


class ImportAllUI(object):
    """
        Helper class to build the Options UI for the fileDialog2 command used when importing all
    """
    
    # What kind of import ?
    importType = jsonTranslatorGlobals.DECODE_AND_ADD

    # What is the text to prepend ?
    importText = kDefaultTextToPrepend
    importTextEditor = None
    
    # Read-Only editors
    notesEditor   = None   # The notes
    previewEditor = None   # The content preview

    @staticmethod
    def addOptions(parent):
        with ParentGuard():
            cmds.setParent(parent)
            cmds.frameLayout(label=kGeneralOptions, collapsable=True, marginWidth= DEFAULT_UI_INDENTATION)

            cmds.radioCollection()
            cmds.radioButton(label=kOverwrite, 
                onCommand=ImportAllUI.setOverwriteImportType, select=True if ImportAllUI.importType==jsonTranslatorGlobals.DECODE_AND_ADD else False)
            cmds.text(label=kOverwriteExplanation, align='left')
            cmds.radioButton(label=kMerge, 
                onCommand=ImportAllUI.setMergeImportType, select=True if ImportAllUI.importType==jsonTranslatorGlobals.DECODE_AND_MERGE else False)
            cmds.text(label=kMergeExplanation, align='left')
            cmds.radioButton(label=kRename, 
                onCommand=ImportAllUI.setRenameImportType, select=True if ImportAllUI.importType==jsonTranslatorGlobals.DECODE_AND_RENAME else False)
            cmds.text(label=kRenameExplanation, align='left')
                        
            with ParentGuard():
                cmds.columnLayout(columnOffset=('left', DEFAULT_UI_INDENTATION))
                cmds.text(label=kTextToPrepend, align='left')
                ImportAllUI.importTextEditor = \
                    cmds.textField(text=ImportAllUI.importText,
                                    textChangedCommand=ImportAllUI.setImportText,
                                    enable= True if ImportAllUI.importType==jsonTranslatorGlobals.DECODE_AND_RENAME else False)

        cmds.text(label=kNotes, align='left')
        ImportAllUI.notesEditor = cmds.scrollField(editable=False)
        cmds.text(label=kPreview, align='left')
        ImportAllUI.previewEditor = cmds.scrollField(editable=False)

    @staticmethod
    def updateContent(parent, selectedFilename):
        """ 
            Update the displayed content following the file selection 
            Note: If the file is not a render setup file or is a directory, 
                  the content (notes & preview) will be empty.
        """
        notesText       = ''
        previewText     = ''

        import os
        if os.path.isfile(selectedFilename):
            with open(selectedFilename, 'r') as file:
                try:
                    import json
                    dict = json.load(file)
                    if jsonTranslatorUtils.isRenderSetup(dict):
                        notesText   = jsonTranslatorUtils.getObjectNotes(dict)
                        previewText = json.dumps(dict, indent=2, sort_keys=True)
                    else:
                        notesText = kUnknownFile
                except:
                    notesText = kUnknownFile

        cmds.scrollField(ImportAllUI.notesEditor, edit=True, text=notesText)
        cmds.scrollField(ImportAllUI.previewEditor, edit=True, text=previewText)

    @staticmethod
    def setOverwriteImportType(data):
        """ 
            Completely overwrite the content of the existing render setup with the imported content.
        """
        ImportAllUI.importType = jsonTranslatorGlobals.DECODE_AND_ADD
        cmds.textField(ImportAllUI.importTextEditor, edit=True, enable=False)

    @staticmethod
    def setMergeImportType(data):
        """ 
            Merge the content of the existing render setup with the imported content. 
            If an unexpected render setup object is found it will renamed using the 'importText'.
        """
        ImportAllUI.importType = jsonTranslatorGlobals.DECODE_AND_MERGE
        cmds.textField(ImportAllUI.importTextEditor, edit=True, enable=False)

    @staticmethod
    def setRenameImportType(data):
        """ 
            Always rename the imported render setup content using the 'importText'.
        """
        ImportAllUI.importType = jsonTranslatorGlobals.DECODE_AND_RENAME
        cmds.textField(ImportAllUI.importTextEditor, edit=True, enable=True)

    @staticmethod
    def setImportText(data):
        """ 
            Preserve the text because it's consumed after the UI is gone.
        """
        ImportAllUI.importText = data


class ImportAOVsUI(object):
    """
        Helper class to build the Options UI for the fileDialog2 command used for importing AOVs
    """
    
    # What kind of import ?
    importType = jsonTranslatorGlobals.DECODE_AND_ADD

    @staticmethod
    def addOptions(parent):
        with ParentGuard():
            cmds.setParent(parent)
            cmds.frameLayout(label=kGeneralOptions, collapsable=True, marginWidth= DEFAULT_UI_INDENTATION)
            cmds.columnLayout(rowSpacing=10)
            cmds.radioCollection()
            cmds.radioButton(label=kOverwrite, 
                onCommand=ImportAOVsUI.setOverwriteImportType, select=True if ImportAOVsUI.importType==jsonTranslatorGlobals.DECODE_AND_ADD else False)
            cmds.text(label=kOverwriteExplanation, align='left')
            cmds.radioButton(label=kMerge, 
                onCommand=ImportAOVsUI.setMergeImportType, select=True if ImportAOVsUI.importType==jsonTranslatorGlobals.DECODE_AND_MERGE else False)
            cmds.text(label=kMergeAOVExplanation, align='left')
            cmds.setParent("..")
            cmds.setParent("..")

    @staticmethod
    def setOverwriteImportType(data):
        """ 
            Completely overwrite the content of the existing render setup with the imported content.
        """
        ImportAOVsUI.importType = jsonTranslatorGlobals.DECODE_AND_ADD

    @staticmethod
    def setMergeImportType(data):
        """ 
            Merge the content of the existing render setup with the imported content. 
            If an unexpected render setup object is found it will renamed using the 'importText'.
        """
        ImportAOVsUI.importType = jsonTranslatorGlobals.DECODE_AND_MERGE
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
