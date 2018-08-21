from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from PySide2.QtWidgets import QGroupBox

import weakref


class RenderLayer(MayaQWidgetBaseMixin, QGroupBox):
    """
    This class represents the property editor view of a layer.
    """

    def __init__(self, item, parent):
        super(RenderLayer, self).__init__(parent=parent)
        self.item = weakref.ref(item)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
