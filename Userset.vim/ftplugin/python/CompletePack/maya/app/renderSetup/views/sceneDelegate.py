import maya
maya.utils.loadStringResourcesForModule(__name__)

from maya.app.renderSetup.views.baseDelegate import BaseDelegate, createPixmap

import maya.app.renderSetup.views.proxy.scene as scene
import maya.app.renderSetup.views.utils as utils

from PySide2.QtCore import Qt
from PySide2.QtGui import QPen

from copy import deepcopy


class SceneDelegate(BaseDelegate):
    """
    This class provides customization of the appearance of items in the Model.
    """
    
    FRAME_INFO_OFFSET = utils.dpiScale(90)
    CURRENT_FRAME = maya.stringTable['y_sceneDelegate.kCurrentFrame' ]
    FRAME_RANGE = maya.stringTable['y_sceneDelegate.kFrameRange' ]
    
    QUICK_SETTINGS_IMAGE = createPixmap(":/RS_quick_settings_popup.png")

    kTooltips = {scene.SET_VISIBILITY_ACTION : maya.stringTable['y_sceneDelegate.kVisibilityToolTip' ],
                 scene.SET_RENDERABLE_ACTION : maya.stringTable['y_sceneDelegate.kRenderableToolTip' ],
                 scene.PRESET_MENU : maya.stringTable['y_sceneDelegate.kPresetMenuToolTip' ],
                 scene.AOVS_MENU : maya.stringTable['y_sceneDelegate.kAovsMenuToolTop' ]}

    def __init__(self, treeView):
        super(SceneDelegate, self).__init__(treeView)

    def _getItem(self, index):
        return self.treeView().model().itemFromIndex(index)

    def _drawFill(self, painter, rect, item, isHighlighted, highlightColor):
        rect2 = deepcopy(rect)
    
        oldPen = painter.pen()
        painter.fillRect(rect2, item.data(Qt.BackgroundRole))

        # draw a 2 pixel border around the box if the item is "active"
        if item.isActive():
            painter.setPen(QPen(item.data(scene.NODE_ACTIVE_FRAME), 2))
            rect2.setLeft(rect2.left() + 2)
            rect2.setRight(rect2.right() - 1)
            rect2.setTop(rect2.top() + 1)
            rect2.setBottom(rect2.bottom() - 1)
            painter.drawRect(rect2)
        painter.setPen(oldPen)

        rect.setLeft(rect.left() + self.COLOR_BAR_WIDTH)

    def _drawArrow(self, painter, rect, item):
        if item.type() != scene.SCENE_CATEGORY_TYPE:
            rect2 = deepcopy(rect)
            rect2.setLeft(rect2.left())
            rect2.setRight(rect2.left() + 3)
            for i in range (1, 7):
                painter.drawPoint(rect2.left(), rect2.top()+4*i)
                painter.drawPoint(rect2.right(), rect2.top()+4*i) 

        super(SceneDelegate, self)._drawArrow(painter, rect, item)

    def _drawText(self, painter, rect, item):
        super(SceneDelegate, self)._drawText(painter, rect, item)
        
        if item.type() == scene.SCENE_CATEGORY_RENDER_SETTINGS_TYPE:
            oldPen = painter.pen()
            painter.setPen(QPen(item.data(Qt.TextColorRole), 1))
            painter.setFont(item.data(Qt.FontRole))
            textRect = deepcopy(rect)
            textRect.setLeft(textRect.left() + self.FRAME_INFO_OFFSET + self.TEXT_LEFT_OFFSET)
            textRect.setRight(textRect.right() - self.TEXT_RIGHT_OFFSET)
            if not item.data(scene.NODE_FRAME_ANIMATION):
                painter.drawText(textRect, Qt.AlignCenter, self.CURRENT_FRAME)
            else:
                painter.drawText(textRect, Qt.AlignCenter, self.FRAME_RANGE % (item.data(scene.NODE_START_FRAME), item.data(scene.NODE_END_FRAME)))
            painter.setPen(oldPen)

    def _addActionIcons(self, painter, rect, item, highlightedColor):
        toolbarCount = item.getActionButtonCount()

        # draw the darkened toolbar frame
        if item.type() != scene.SCENE_CATEGORY_RENDER_SETTINGS_TYPE and item.type() != scene.SCENE_CATEGORY_AOVS_TYPE:
            self.drawToolbarFrame(painter, rect, toolbarCount)

        start = self.ACTION_BORDER
        for iconIndex in range(0, toolbarCount):
            actionName = item.getActionButton(iconIndex)
            checked = False
            pixmap = None
            if (actionName == scene.SET_VISIBILITY_ACTION):
                pixmap = self.VISIBILITY_IMAGE
                checked = item.data(scene.NODE_VISIBLE)
            elif (actionName == scene.SET_RENDERABLE_ACTION):
                pixmap = self.RENDERABLE_IMAGE
                checked = item.data(scene.NODE_RENDERABLE)
            elif (actionName == scene.PRESET_MENU or actionName == scene.AOVS_MENU):
                pixmap = self.QUICK_SETTINGS_IMAGE

            start += self.ACTION_WIDTH
            self.drawAction(painter, actionName, pixmap, rect.right() - start, rect.top() + self.ICON_TOP_OFFSET,
                          highlightedColor if checked else None, False, None)

        if self.lastHitAction:
            try:
                item.setToolTip(self.kTooltips[self.lastHitAction])
            except KeyError:
                item.setToolTip("")
        else:
            item.setToolTip("")# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
