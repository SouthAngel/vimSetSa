from maya import cmds,mel
from functools import partial

__all__ = ['menuItemToShelf']

def menuItemToShelf(shelf, item):
    """
    Create a shelfButton on a shelf which acts like a menuItem.
    
    Note: If item has dragMenuCommand defined, then in will be executed,
    and the result will be used as the new button's command.
    Otherwise item's command will be used as the new button's command.
    
    If item has dragDoubleClickCommand defined, it will be used as the new
    button's doubleClickCommand.
    
    shelf - the shelf to put the new shelfButton on
    item - the menuItem to copy
    
    \return the path of the created shelfButton
    """
    cmds.setParent(shelf)
    
    # shortcut for menuItem queries
    miq = partial(cmds.menuItem, item, q=True)

    # Get the commands for the shelf button
    dmc,dmclang = miq(dragMenuCommand=True), miq(dragMenuCommand=True, stp=True)
    shelfcmd,shelfcmdlang = None,dmclang
    if dmc and (callable(dmc) or len(dmc)):
        if 'python' == dmclang:
            if callable(dmc):
                shelfcmd = dmc()
            else:
                shelfcmd = eval(dmc)
        else:
            shelfcmd = mel.eval(dmc)
    else:
        shelfcmd,shelfcmdlang = miq(command=True), miq(command=True, stp=True)
        if shelfcmd:
            if miq(isCheckBox=True) and not callable(shelfcmd):
                if miq(cb=True):
                    subStr = '0'
                else:
                    subStr = '1'
                shelfcmd = shelfcmd.replace('#1', subStr)
            elif miq(isRadioButton=True):
                shelfcmd = shelfcmd.replace('#1', '1')
    # Get the double-click command for the shelf button
    dcc,dcclang = miq(dragDoubleClickCommand=True), miq(dragDoubleClickCommand=True, stp=True)

    # Get the image for shelf button
    image = miq(image=True)
    imageOverlayLabel = ""
    if not len(image):
        image = miq(familyImage=True)
        if not len(image):
            if shelfcmdlang == "python":
                image = "pythonFamily.png"
            else:
                image = "commandButton.png"
        # create overlay if necessary
        imageOverlayLabel = miq(iol=True)
        if not len(imageOverlayLabel):
            # Use the first character of each word in the 
            # menuItem -label if it is more than one word
            # else use the first 3 characters of the menu label.
            label = miq(label=True)
            if miq(isOptionBox=True):
                # Try to Use the "annotation" string if it exists
                # else use the menuItem name.
                label = miq(annotation=True)
                if not len(label):
                    label = miq(label=True)
            # If we have a good label then create a short overlay string
            if len(label):
                tokens = label.split()
                if len(tokens) == 1:
                    if len(label) > 3:
                        imageOverlayLabel = label[0:4]
                    else:
                        imageOverlayLabel = label
                else:
                    imageOverlayLabel = ''.join([tok[0] for tok in tokens])
                # Now set the image overlay label
                cmds.menuItem(item, e=True, iol=imageOverlayLabel)
    
    # And now... create the shelfButton
    btn = cmds.shelfButton(image1=image,
                           imageOverlayLabel=imageOverlayLabel,
                           label=miq(label=True),
                           style=cmds.shelfLayout(shelf, q=True, style=True),
                           width=cmds.shelfLayout(shelf, q=True, cellWidth=True),
                           height=cmds.shelfLayout(shelf, q=True, cellHeight=True),
                           ann=miq(ann=True))
    # add the commands
    if shelfcmd:
        cmds.shelfButton(btn, e=True, command=shelfcmd, stp=shelfcmdlang)
    if dcc:
        cmds.shelfButton(btn, e=True, doubleClickCommand=dcc, stp=dcclang)
    return btn
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
