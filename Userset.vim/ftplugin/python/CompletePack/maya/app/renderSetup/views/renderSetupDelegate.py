import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtCore import Qt, QRect
from PySide2.QtGui import QPainter, QColor, QBrush, QCursor, QFontMetrics, QPen
from PySide2.QtWidgets import QLineEdit

import maya.app.renderSetup.views.baseDelegate as baseDelegate

import maya.app.renderSetup.views.proxy.renderSetup as renderSetup
import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles
import maya.app.renderSetup.views.utils as utils

import maya.app.renderSetup.model.selector as selector

from copy import deepcopy

""" Create a dictionary of pixmaps to use for filtering
    These can be looked up by filter type """
def createFilterPixmaps():    
    filterIcons = {}
    filterIcons[selector.Filters.kAll]        = baseDelegate.createPixmap(":/filtersOff.png")
    filterIcons[selector.Filters.kTransforms] = baseDelegate.createPixmap(":/out_transform.png")
    filterIcons[selector.Filters.kShapes]     = baseDelegate.createPixmap(":/out_mesh.png")
    filterIcons[selector.Filters.kShaders]    = baseDelegate.createPixmap(":/out_blinn.png")
    filterIcons[selector.Filters.kLights]     = baseDelegate.createPixmap(":/out_spotLight.png")
    filterIcons[selector.Filters.kSets]       = baseDelegate.createPixmap(":/out_objectSet.png")
    filterIcons[selector.Filters.kTransformsAndShapes]     = baseDelegate.createPixmap(":/RS_multiple_filters.png")
    filterIcons[selector.Filters.kTransformsShapesShaders] = filterIcons[selector.Filters.kTransformsAndShapes]
    filterIcons[selector.Filters.kCameras] = baseDelegate.createPixmap(":/out_camera.png")
    filterIcons[selector.Filters.kGenerators] = baseDelegate.createPixmap(":/out_polySphere.png")
    filterIcons[selector.Filters.kShadingEngines] = baseDelegate.createPixmap(":/out_shadingEngine.png")
    filterIcons[selector.Filters.kCustom] = baseDelegate.createPixmap(":/filtersOn.png")
    return filterIcons


class RenderSetupDelegate(baseDelegate.BaseDelegate):
    """
    This class provides customization of the appearance of items in the Model.
    """

    # Constants
    HIGHLIGHTED_FILL_OFFSET = 1
    INFO_COLOR = QColor(255, 0, 0)

    LEFT_NON_TEXT_OFFSET = utils.dpiScale(25.5)
    RIGHT_NON_TEXT_OFFSET = utils.dpiScale(6)

    DISABLED_IMAGE   = baseDelegate.createPixmap(":/RS_disable.png")
    ISOLATE_IMAGE    = baseDelegate.createPixmap(":/RS_isolate.png")
    INVALID_IMAGE    = baseDelegate.createPixmap(":/RS_invalid.png")
    DISCLOSURE_IMAGE = baseDelegate.createPixmap(":/RS_disclosure_triangle.png")

    # create a collection of pixmaps used for filters that can be looked up by filter type
    _kFilterIcons = createFilterPixmaps()

    kTooltips = {renderSetup.SET_VISIBILITY_ACTION : maya.stringTable['y_renderSetupDelegate.kVisibilityToolTip' ],
                 renderSetup.SET_RENDERABLE_ACTION : maya.stringTable['y_renderSetupDelegate.kRenderableToolTip' ],
                 renderSetup.SET_ENABLED_ACTION : maya.stringTable['y_renderSetupDelegate.kEnabledToolTip' ],
                 renderSetup.SET_ISOLATE_SELECTED_ACTION : maya.stringTable['y_renderSetupDelegate.kIsolateToolTip' ],
                 renderSetup.FILTER_MENU : maya.stringTable['y_renderSetupDelegate.kFiltersToolTip' ]}

    @staticmethod
    def getFilterIcon(filter):
        # filter can be an integer (built-in type filter) or an iterable of type names
        if not isinstance(filter,list) and filter in RenderSetupDelegate._kFilterIcons:
            return RenderSetupDelegate._kFilterIcons[filter]
        try: filters = list(filter)
        except: return None
        
        if len(filters) > 1:
            return RenderSetupDelegate._kFilterIcons[selector.Filters.kCustom]
        elif len(filters) > 0:
            f = filters[0]
            if f == 'shader/surface':
                return RenderSetupDelegate._kFilterIcons[selector.Filters.kShaders]
            if f == 'shader/displacement':
                return baseDelegate.createPixmap(":/render_displacementShader.png")
            if f == 'shader/volume':
                return baseDelegate.createPixmap(":/render_volumeFog.png")
            if f == 'geometry':
                return baseDelegate.createPixmap(":/out_polySphere.png")
            try: return baseDelegate.createPixmap(":/render_%s.png" % f)
            except: pass
            try: return baseDelegate.createPixmap(":/out_%s.png" % f)
            except: pass
        return None

    def __init__(self, treeView):
        super(RenderSetupDelegate, self).__init__(treeView)

    def _getItem(self, index):
        return self.treeView().model().itemFromIndex(index)

    def _drawColorBar(self, painter, rect, item):
        rect2 = deepcopy(rect)
        rect2.setRight(rect2.left() + self.COLOR_BAR_WIDTH)
        painter.fillRect(rect2, item.data(renderSetupRoles.NODE_COLOR_BAR))
        
        if item.type()==renderSetup.RENDER_OVERRIDE_TYPE and item.isLocalRender():
            diameter = rect2.width()-2
            rect3 = QRect(rect2.x()+1, rect2.y() + (rect2.height()-diameter)/2, diameter, diameter)
            brush = painter.brush()
            pen = painter.pen()
            hints = painter.renderHints()
        
            painter.setRenderHint(QPainter.Antialiasing, on=True)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(67,79,70), style=Qt.SolidPattern))
            painter.drawEllipse(rect3)
        
            painter.setRenderHints(hints)
            painter.setPen(pen)
            painter.setBrush(brush)

    def _drawFill(self, painter, rect, item, isHighlighted, highlightColor):
        rect.setLeft(rect.left() + self.COLOR_BAR_WIDTH+1)

        oldPen = painter.pen()
        
        if isHighlighted:
            rect.setLeft(rect.left() + self.HIGHLIGHTED_FILL_OFFSET)
            if not item.data(renderSetupRoles.NODE_ENABLED):
                painter.drawTiledPixmap(rect, baseDelegate.BaseDelegate.DISABLED_HIGHLIGHT_IMAGE)
            else:
                painter.fillRect(rect, highlightColor)
            rect.setLeft(rect.left() - self.HIGHLIGHTED_FILL_OFFSET)
        else:
            painter.fillRect(rect, item.data(Qt.BackgroundRole))
            if not item.data(renderSetupRoles.NODE_ENABLED):
                painter.drawTiledPixmap(rect, baseDelegate.BaseDelegate.DISABLED_BACKGROUND_IMAGE)
        
        if item.isActive():
            painter.setPen(QPen(item.data(renderSetupRoles.NODE_COLOR_BAR), 2))
            rect2 = deepcopy(rect)
            rect2.setRight(rect2.right() - 1)
            rect2.setTop(rect2.top() + 1)
            rect2.setBottom(rect2.bottom() - 1)
            painter.drawRect(rect2)

        painter.setPen(oldPen)

    def _addActionIcons(self, painter, rect, item, highlightedColor):
        top = rect.top() + (self.ICON_TOP_OFFSET)

        start = self.ACTION_BORDER
        count = item.getActionButtonCount()
        toolbarCount = count
        if item.type() == renderSetup.COLLECTION_TYPE:
            toolbarCount -= 1

        # draw the darkened toolbar frame
        self.drawToolbarFrame(painter, rect, toolbarCount)

        for iconIndex in range(0, count):
            actionName = item.getActionButton(iconIndex)
            pixmap = None
            drawDisclosure = False
            extraPadding = 0
            checked = False

            borderColor = None
            if (actionName == renderSetup.SET_VISIBILITY_ACTION):
                pixmap = self.VISIBILITY_IMAGE
                checked = item.data(renderSetupRoles.NODE_VISIBLE)
                if checked and item.data(renderSetupRoles.NODE_NEEDS_UPDATE):
                    borderColor = self.INFO_COLOR
            elif (actionName == renderSetup.SET_RENDERABLE_ACTION):
                pixmap = self.RENDERABLE_IMAGE
                checked = item.data(renderSetupRoles.NODE_RENDERABLE)
            elif (actionName == renderSetup.SET_ENABLED_ACTION):
                pixmap = RenderSetupDelegate.DISABLED_IMAGE
                checked = not item.data(renderSetupRoles.NODE_SELF_ENABLED)
            elif (actionName == renderSetup.SET_ISOLATE_SELECTED_ACTION):
                pixmap = RenderSetupDelegate.ISOLATE_IMAGE
                checked = item.data(renderSetupRoles.NODE_ISOLATE_SELECTED)
            elif (actionName == renderSetup.FILTER_MENU):
                filter = item.model.getSelector().getFilterType()
                if filter == selector.Filters.kCustom:
                    filter = item.model.getSelector().getTypeFilters()
                pixmap = RenderSetupDelegate.getFilterIcon(filter)
                left = rect.right() - (start + self.ACTION_WIDTH + 4)
                if pixmap:
                    self.drawPixmap(painter, pixmap, left, top)
                continue

            start += self.ACTION_WIDTH + extraPadding
            self.drawAction(painter, actionName, pixmap, rect.right() - start, top, highlightedColor if checked else None, drawDisclosure, borderColor)

        if self.lastHitAction:
            # MAYA-66647 - This should be made into a separate action instead of a conditional action
            if self.lastHitAction == renderSetup.SET_VISIBILITY_ACTION and item.data(renderSetupRoles.NODE_NEEDS_UPDATE):
                item.setToolTip(maya.stringTable['y_renderSetupDelegate.kUpdateVisibilityToolTip' ])
            else:
                item.setToolTip(self.kTooltips[self.lastHitAction])
        else:
            item.setToolTip("")

    def createEditor(self, parent, option, index):
        """ Creates the double-click editor for renaming render setup entries. The override entry is right aligned. """
        editor = QLineEdit(parent)
        item = self._getItem(index)
        if item.type() == renderSetup.RENDER_OVERRIDE_TYPE:
            editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return editor

    def getTextRect(self, rect, item):
        newRect = super(RenderSetupDelegate, self).getTextRect(rect, item)
        newRect.setBottom(rect.bottom() - self.BOTTOM_GAP_OFFSET)
        if item.type() == renderSetup.RENDER_LAYER_TYPE:
            newRect.setRight(rect.right() - self.LAYER_TEXT_RIGHT_OFFSET)
        elif item.type() == renderSetup.COLLECTION_TYPE:
            newRect.setRight(rect.right() - self.COLLECTION_TEXT_RIGHT_OFFSET)
        elif item.type() == renderSetup.RENDER_OVERRIDE_TYPE:
            warning = item.data(renderSetupRoles.NODE_WARNING)
            if not warning:
                newRect.setRight(rect.right() - self.TEXT_RIGHT_OFFSET)
            else:
                newRect.setRight(rect.right() - (self.TEXT_RIGHT_OFFSET + baseDelegate.BaseDelegate.WARNING_ICON_WIDTH + baseDelegate.BaseDelegate.ACTION_BORDER))


        return newRect

    def updateEditorGeometry(self, editor, option, index):
        """ Sets the location for the double-click editor for renaming render setup entries. """
        item = self._getItem(index)
        rect = self.getTextRect(option.rect, item)

        indent = item.depth() * self.treeView().indentation()
        if item.type() == renderSetup.RENDER_LAYER_TYPE or item.type() == renderSetup.COLLECTION_TYPE:
            leftOffset = indent + item.data(renderSetupRoles.NODE_HEADING_WIDTH) + self.LEFT_NON_TEXT_OFFSET
            rect.setLeft(leftOffset)

        editor.setGeometry(rect)

    def _drawWarning(self, painter, rect, item):
        warning = item.data(renderSetupRoles.NODE_WARNING)
        if warning and len(warning) > 0:
            fm = QFontMetrics(self.treeView().font())
            if item.type() == renderSetup.RENDER_OVERRIDE_TYPE:
                left = self.getTextRect(rect, item).right() + baseDelegate.BaseDelegate.ACTION_BORDER
            else:
                left = self.getTextRect(rect, item).left() + fm.boundingRect(item.data(Qt.DisplayRole)).width() + baseDelegate.BaseDelegate.ACTION_BORDER
            top = rect.top() + baseDelegate.BaseDelegate.ICON_TOP_OFFSET
            painter.drawPixmap(left, top, baseDelegate.BaseDelegate.WARNING_IMAGE)

            iconRect = QRect(left, top, baseDelegate.BaseDelegate.WARNING_ICON_WIDTH, baseDelegate.BaseDelegate.WARNING_ICON_WIDTH)
            p = self.treeView().mapFromGlobal(QCursor.pos())
            if iconRect.contains(p):
                item.setToolTip(warning)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
