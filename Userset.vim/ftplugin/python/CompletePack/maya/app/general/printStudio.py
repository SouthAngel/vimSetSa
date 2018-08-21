import maya
maya.utils.loadStringResourcesForModule(__name__)

import os
import sys
import urllib
import urllib2
import json
import subprocess
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om

from sys import platform as _platform
if _platform == "win32":
    import _winreg

"""
This is the current json info for Print Studio
{
   "print_studio" : {
      "major": 1,
      "minor": 5,
      "minor_minor": 0,
      "url": "http://www.autodesk.com",
      "windows_installer_url": "http://labs-download.autodesk.com/us/labs/trials/worldwide/Autodesk_PrintStudio_v1.5.0_Win64.exe",
      "mac_os_installer_url": "http://labs-download.autodesk.com/us/labs/trials/worldwide/Autodesk_PrintStudio_v1.5.0_MAC_OSX.pkg"
   }
}
"""

printStudioPath = None
downloadInfo = None

def downloadPrintStudio(window, tabLayout, progressBar):
    """
    http://stackoverflow.com/questions/22676/how-do-i-download-a-file-over-http-using-python
    """
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar');
    cmds.progressBar(gMainProgressBar, query=True, isCancelled=True)
    cmds.tabLayout(tabLayout, edit=True, selectTabIndex=2)
    url = printStudioDownloadURL()
    if url is None:
        return
    om.MGlobal.displayInfo(maya.stringTable['y_printStudio.kDownloadingPrintStudio' ])
    updatesDir = cmds.about(preferences=True) + '/updates'
    if not os.path.isdir(updatesDir):
        os.mkdir(updatesDir)
    file_name = url.split('/')[-1]
    download_file = os.path.join(updatesDir, file_name)
    u = urllib2.urlopen(url)
    f = open(download_file, 'wb')
    file_size = downloadInfo['size']
#    print "Downloading: %s Bytes: %s" % (file_name, file_size)
    cmds.progressBar(progressBar, edit=True, maxValue=file_size)

    cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, maxValue=file_size)

    file_size_dl = 0
    block_sz = 8192
    remove = False
    while True:
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            remove = True
            break
        buffer = u.read(block_sz)
        if not buffer:
            break
    
        file_size_dl += len(buffer)
        f.write(buffer)
        if file_size != 0:
#            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
#            status = status + chr(8)*(len(status)+1)
            cmds.progressBar(progressBar, edit=True, progress=file_size_dl)
            cmds.progressBar(gMainProgressBar, edit=True, progress=file_size_dl)
#            print status,
    
    f.close()
    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
    if remove:
        os.remove(download_file)
    else:
        """
        show the downloaded file
        """
        if sys.platform.startswith('darwin'):
            subprocess.call(["open", "-R", download_file])
        elif sys.platform.startswith('linux'):
            subprocess.call(["kde-open", download_file])
        elif sys.platform.startswith('win'):
            subprocess.call(["explorer.exe", "/select,", os.path.normpath(download_file)])
    cmds.deleteUI(window, window=True)

def getPrintStudioDialog():
    global downloadInfo
    window = cmds.window(title=maya.stringTable['y_printStudio.kPrintStudioDownload' ], widthHeight=(340, 180), menuBar=False, sizeable=False)

    formLayout = cmds.formLayout()
    tabLayout = cmds.tabLayout(innerMarginWidth=0, innerMarginHeight=0, tabsVisible=False)
    cmds.formLayout(formLayout, edit=True, attachForm=((tabLayout, 'top', 0), (tabLayout, 'left', 0), (tabLayout, 'bottom', 0), (tabLayout, 'right', 0)))

    # Tab 1 - Print Studio is not currently installed
    cmds.columnLayout(width=340)
    cmds.columnLayout(width=340)
    cmds.text(width=340, height=60, label=maya.stringTable['y_printStudio.kNotIntalled1' ], align='center')
    cmds.text(width=340, height=16, label=maya.stringTable['y_printStudio.kNotIntalled2' ], align='center')
    sizeInfo = ''
    if printStudioDownloadURL() is not None:
        file_name = downloadInfo['url'].split('/')[-1]
        sizeInfo = '%s (%d MB)' % (file_name, int(round(downloadInfo['size']/1048576.0)))
    cmds.text(width=340, height=24, label=sizeInfo, align='center')
    cmds.separator(width=340, height=44, style='none')
    cmds.separator(width=340)
    cmds.setParent('..')
    cmds.rowLayout(numberOfColumns=5, columnAttach=[(1, 'left', 4), (5, 'right', 4)])
    aboutCommand = lambda widget: cmds.showHelp('https://ember.autodesk.com/overview#software', absolute=True)
    aboutButton = cmds.button(width=120, label=maya.stringTable['y_printStudio.kAboutPrintStudio' ], command=aboutCommand)
    cmds.separator(width=4, horizontal=False)
    downloadCommand = lambda widget: downloadPrintStudio(window=window, tabLayout=tabLayout)
    downloadButton = cmds.button(width=94, label=maya.stringTable['y_printStudio.kDownload' ], command=downloadCommand)
    cmds.separator(width=4, horizontal=False)
    cancelCommand = lambda widget: cmds.deleteUI(window, window=True)
    cmds.button(width=94, label=maya.stringTable['y_printStudio.kCancel' ], command=cancelCommand)
    cmds.setParent('..')
    cmds.setParent('..')

    # Tab 2 - Downloading Print Studio Installer
    cmds.columnLayout(width=340)
    cmds.columnLayout(width=340)
    cmds.text(width=340, height=60, label=maya.stringTable['y_printStudio.kDownloading' ], align='center')
    cmds.rowLayout(numberOfColumns=1, columnAttach=[(1, 'left', 30)])
    progressBar = cmds.progressBar(width=270, height=16)
    cmds.setParent('..')
    cmds.separator(width=340, height=4, style='none')
    cmds.text(width=340, height=60, label=maya.stringTable['y_printStudio.kPressToCancel' ], align='center')

    downloadCommand = lambda widget: downloadPrintStudio(window=window, tabLayout=tabLayout, progressBar=progressBar)
    cmds.button(downloadButton, edit=True, command=downloadCommand)

    cmds.tabLayout(tabLayout, edit=True, selectTabIndex=1)
    cmds.showWindow(window)

def printStudioDownloadURL():
    # cache download information
    global downloadInfo
    if downloadInfo is not None:
        return downloadInfo['url']
    try:
        downloadInfo = {}
        url = "https://api.spark.autodesk.com/api/v1/print/version"
        jsonurl = urllib.urlopen(url)
        psData = json.loads(jsonurl.read())
        if _platform == "win32":
            downloadInfo['url'] = psData["print_studio"]["windows_installer_url"]
        elif _platform == "darwin":
            downloadInfo['url'] = psData["print_studio"]["mac_os_installer_url"]
        u = urllib2.urlopen(downloadInfo['url'])
        meta = u.info()
        downloadInfo['size'] = int(meta.getheaders("Content-Length")[0])
        return downloadInfo['url']
    except:
        pass

    return None

def printStudioInstalled():
    # Check if we already know where Print Studio is
    global printStudioPath
    if printStudioPath is not None:
        return printStudioPath

    try:
        om.MGlobal.displayInfo(maya.stringTable['y_printStudio.kDetectPrintStudio' ])
        if sys.platform.startswith('darwin'):
            # The bundle search is pretty slow, so see if Print Studio
            # is where we expect it
            #
            p = '/Applications/Autodesk/Autodesk Print Studio/Print Studio.app/Contents/MacOS/Print Studio'
            if not os.path.isfile(p):
                p = None
                cmd = 'mdfind kMDItemCFBundleIdentifier = "com.autodesk.spark.printstudio"'
                pipe = os.popen(cmd, 'r')
                while True:
                    c = pipe.readline()
                    if not c:
                        break
                    p = c
                if p is not None:
                    p = os.path.join(p, 'Contents/MacOS/Print Studio')
            if p is not None:
                printStudioPath = p
        elif sys.platform.startswith('win'):
            aReg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)        
            aKey = _winreg.OpenKey(aReg, "SOFTWARE\\Autodesk\\{4B22C678-3E31-4E8E-BC6C-21C778D25420}")
            p = _winreg.QueryValueEx( aKey, "ExecPath")
            printStudioPath = p[0]
    except:
        pass

    return printStudioPath

def exportFile():
    om.MGlobal.displayInfo(maya.stringTable['y_printStudio.kExportFile' ])
    if not cmds.pluginInfo( "objExport", q=True, loaded=True):
        cmds.loadPlugin("objExport")
        if not cmds.pluginInfo( "objExport", q=True, loaded=True):
            return None

    tempDir = cmds.internalVar( userTmpDir=True )
    tempFile = os.path.join(tempDir, 'mayaToPrintStudio.obj')

    tempFile = cmds.file( tempFile, force=True, exportSelected=True, typ="OBJexport", pr=True, es=True)

    return tempFile

def printStudio():
    path = printStudioInstalled()
    if path is not None:
        file = exportFile()
        if file is not None:
            om.MGlobal.displayInfo(maya.stringTable['y_printStudio.kStartPrintStudio' ])
            up = cmds.upAxis( q=True, axis=True )
            axis = "-yup"
            if "z" == up:
                axis = "-zup"

            unit = cmds.currentUnit( query=True, linear=True)
            if unit not in ["cm", "mm", "in"]:
                unit = "cm"

            if sys.platform.startswith('darwin'):
                cmd = 'open "spark-printstudio:///-import=%s&%s&-units=%s" -b com.autodesk.spark.printstudio' % (file, axis, unit)
                os.system(cmd)
            elif sys.platform.startswith('win'):
                subprocess.Popen([path, "-import", file, axis, "-units", unit])
            om.MGlobal.displayInfo('')
        else:
            cmds.warning(maya.stringTable['y_printStudio.kExportError' ])
    else:
        getPrintStudioDialog()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
