""" Singleton for Render Layer switch observation

    This module is used to notify of progress during layer switching, which
    can be a lengthy operation.
"""

import maya.app.renderSetup.model.observable as observable

class RenderLayerSwitchObservable(object):

    _instance = None

    def __init__(self):
        self.switchObservable = observable.Observable()

    def addRenderLayerSwitchObserver(self, obsMethod):
        self.switchObservable.addItemObserver(obsMethod)
        
    def removeRenderLayerSwitchObserver(self, obsMethod):
        self.switchObservable.removeItemObserver(obsMethod)

    def notifyRenderLayerSwitchObserver(self):
        self.switchObservable.itemChanged()

    @staticmethod
    def getInstance():
        if not RenderLayerSwitchObservable._instance:
            RenderLayerSwitchObservable._instance = RenderLayerSwitchObservable()
        return RenderLayerSwitchObservable._instance

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
