"""
Maya's EDL Importer and Exporter. Reads data from a format-specific EDL translator and generates the appropriate shots and tracks in Maya. Or vice versa.
"""
import os
import re
import maya
import tempfile
import maya.OpenMaya as OpenMaya
import maya.OpenMayaRender as OpenMayaRender
import maya.OpenMayaMPx as OpenMayaMPx
import maya.cmds as cmds
from maya.app.edl.fcp import *


doMel = maya.mel.eval


mayaFrameRates = { 	15 : "game",
					24 : "film",
					25 : "pal",
					30 : "ntsc",
					48 : "show",
					50 : "palf",
					60 : "ntscf" }

def _getValidClipObjectName( clipName, isVideo ):
    validName = clipName.split( "/" )[-1:][0].split( "\\" )[-1:][0].split( "." )[0]
    validName = re.sub('[\W]+', '', validName)

    if len( validName ) == 0:
        if isVideo:
            validName = "shot"
        else:
            validName = "audio"

    return validName

def _setTimeCode( timecode ):

	fields = timecode.split( ":" )
	
	if len( fields ) == 4:
		cmds.timeCode( e=1, productionStartHour=int(fields[0]), productionStartMinute = int(fields[1]), productionStartSecond = int(fields[2]), productionStartFrame = int(fields[3]), mayaStartFrame = 0 )

def _nameToNode( name ):
    selectionList = OpenMaya.MSelectionList()
    selectionList.add( name )
    node = OpenMaya.MObject()
    selectionList.getDependNode( 0, node )
    return node

class ImportExport(OpenMayaMPx.MPxCommand):
	def __init__(self):
		OpenMayaMPx.MPxCommand.__init__(self)

		self.translator = None

		# store a mapping between shot/audio nodes and the associated clipitem
		# elements. This is needed to properly link audio and video clips 
		# together in Maya
		self.shotNodes = {} 

		self.errorFileName = ""
		self.errorHandler = None
		self.warningHandler = None

	def __del__(self):
		self._closeLoggingHandlers()

	def _setupLoggingHandlers(self):
		"""
		Setup two handlers. One that will display both warnings and errors to stderr. 
		And another that will only log errors to a file. If we have no errors at all,
		then, we can continue. Otherwise, we must undo the import.
		"""
		fileBaseName = os.path.splitext(self.translator.fileName)[0]
		self.errorFileName = (fileBaseName + "_error.log")

		if os.path.exists(self.errorFileName):
			os.remove(self.errorFileName)

		errorFmt = logging.Formatter("EDL Import: %(message)s")
		warningFmt = logging.Formatter("%(levelname)s %(message)s")

		self.errorHandler = logging.FileHandler(self.errorFileName, mode="w")
		self.errorHandler.setLevel(logging.ERROR)
		self.errorHandler.setFormatter(errorFmt)

		self.warningHandler = logging.StreamHandler()
		self.warningHandler.setLevel(logging.WARNING)
		self.warningHandler.setFormatter(warningFmt)

		self.translator.logger.addHandler(self.errorHandler)
		self.translator.logger.addHandler(self.warningHandler)
		
	def _closeLoggingHandlers(self):
		self.errorHandler.close()
		self.warningHandler.close()

		self.translator.logger.removeHandler(self.errorHandler)
		self.translator.logger.removeHandler(self.warningHandler)

		# TODO check that the error handler file is empty. If not, raise exception?
		# Echo all the warnings in the warning file to the script editor
		if os.path.exists(self.errorFileName):
			fileSize = os.path.getsize(self.errorFileName)
			os.remove(self.errorFileName)
			
			if fileSize != 0:
				# TODO: figure out why calling self.undoIt() is failing!!
				raise Exception("Critical errors during EDL import/export of %s" % self.translator.fileName)

class Importer(ImportExport):
	def __init__(self):
		ImportExport.__init__(self)

		# dictionary with sequence-specific information. Populated
		# by Translator.getSequence
		self.seq_info = {}

		# key = clip elements
		# value = Maya shot/audio nodes
		# Needed to for linking of audio and video
		self.clip_dict = {}

		# Store the minimum start frame that we set for any audio/video node.
		# Needed to apply the start frame override
		self.minFrameInFile = None

		# The frame the sequence should start at if we're overriding
		# the values in the file.
		self.startFrameOverride = None

	def setStartFrameOverride(self, frame):
		self.startFrameOverride = float(frame)

	def doIt(self, fileName):
		"""
		Reads an EDL file into Maya. Will generate shots, tracks and audio in Maya that 
		corresponds to the tracks and clips in the EDL.
		"""
		ext = os.path.splitext(fileName)[-1]
		if ext.lower() == ".xml":
			self.translator = FCP(fileName)
		elif ext.lower() == ".aaf":
			tempdir = tempfile.gettempdir()			
			taskId = cmds.aaf2fcp(srcFile=fileName,dstPath=tempdir)
			cmds.aaf2fcp(waitCompletion=taskId)			
			# construct the filename and read it			
			basePath = os.path.splitext(fileName)[0]
			baseName = os.path.basename(basePath)
			fcpTempfile = tempdir + "/" + baseName + ".xml"
			self.translator = FCP(fcpTempfile)
			cmds.aaf2fcp(terminate=taskId)			
			
		# TODO: determine if this should return quietly, or raise an exception
		if self.translator is None:
			self._closeLoggingHandlers()
			raise Exception("Could not find translator for EDL file: %s" % fileName)
	
		self._setupLoggingHandlers()	

		self.translator.readFromFile()
		self.seq_info = self.translator.getSequence()

		# Set the maya frame rate to whatever the sequence's frame rate is
		timeUnit = self.seq_info.get("framerate", None)
		mayaTimeUnit = mayaFrameRates.get(timeUnit, None)
		if mayaTimeUnit is None:
			if timeUnit is None:
				self.translator.warning("Sequence did not specify frame rate. Using current frame rate")
			else:
				self.translator.error("Maya does not support frame rate: %d" % timeUnit)
		else:
			cmds.currentUnit(time=mayaTimeUnit)
			
		# read timecode
		timecode = self.seq_info.get("timecode", None)

		if timecode is not None:
			_setTimeCode( timecode )

		video_tracks = self.seq_info.get("video_tracks", None)

		# Inverting track orders to respect original FCP evaluation order
		# audio dont need to be inverted
		video_tracks.reverse()
		if video_tracks is not None:
			for track in video_tracks:
				self._readTrack(track, True)
		
		audio_tracks = self.seq_info.get("audio_tracks", None)
		
		if audio_tracks is not None:
			for track in audio_tracks:
				self._readTrack(track, False)
		
		self._applyLinks()

		self._applyStartFrameOverride()

		self._closeLoggingHandlers()

	def _applyLinks(self):
		"""
		Read the link information and associate audio clips to shots
		"""

		# Link info is a list of dictionaries
		link_info = self.translator.getLinks()
		for link in link_info:
			# note: Maya currently only supports linking of one
			# audio clip to one video clip.
			audio = None
			video = None
			for clip in link.itervalues():
				mayaNode = self.clip_dict.get(clip, None)
				if mayaNode is not None:
					type = cmds.nodeType(mayaNode)
					if type == "shot":
						video = mayaNode
					elif type == "audio":
						audio = mayaNode
			if audio is not None and video is not None:
				cmds.shot(video, e=1, linkAudio=audio)

	def _applyStartFrameOverride(self):
		"""
		If a start frame override has been set, then adjust the sequence start frames
		for all audio and video clips so that the earliest shot/audio that we created
		is at the specified frame.
		"""
		if self.startFrameOverride is None or self.minFrameInFile is None:
			return

		offset = (self.minFrameInFile - self.startFrameOverride)

		for clip in self.clip_dict.itervalues():
			if clip is None:
				# TODO: raise warning here. We failed to create a matching 
				# shot/audio node for some reason
				pass
			else:
				type = cmds.nodeType(clip)
				if type == "shot":
					start = float(cmds.shot(clip, q=1, sequenceStartTime=1)) - offset 
					end = float(cmds.shot(clip, q=1, sequenceEndTime=1)) - offset 
					cmds.shot(clip, e=1, sequenceStartTime=start, sequenceEndTime=end)
				elif type == "audio":
					start = float(cmds.sound(clip, q=1, offset=1)) - offset 
					cmds.sound(clip, e=1, offset=start)

	def _checkFrameRates(self, elem, elem_info):
		"""
		Check that the frame rate for the given element matches the sequence (i.e Maya) frame rate.
		If it does not, log an error.
		"""
		fps = cmds.currentUnit(q=1, time=1)
		fps = [k for k, v in mayaFrameRates.iteritems() if v == fps][0]
		elemFPS = elem_info.get("framerate", None)
		if elemFPS is not None and elemFPS != fps:
			self.translator.logger.error("Frame rate for %s does not not match sequence frame rate" % self.translator.formatErrorElement(elem))

	def _readTrack(self, track, isVideo):
		track_info = self.translator.getTrack(track)

		# Ensure that track frame rate matches sequence frame rate
		self._checkFrameRates(track, track_info)

		trackNum = 0
		if isVideo:
			trackNum = cmds.shotTrack(q=1, numTracks=1) + 1
		else:
			trackNum = cmds.audioTrack(q=1, numTracks=1) + 1

		locked = track_info.get("locked", False)
			
		# Precompute the real start, stop and centers for every clipItem
		# these aren't necessarily the one read from the file when transition clips are involved
		# in these cases values are always -1
		
		transitions = []		#boolean that indicates if the clip at index is a clip or a transition
		starts = []
		ends = []
		alignments = []			# alignment value read from the XML file, valid only for transitions
		in_adjustments = []     # media offset that must be apply to the right due to the removal of overlaps
		
		# Initialise the starts and ends with the XML file values		
		for clip in track_info["clip_list"]:
			isTransition, start, end, alignment = self._getTransitionInfo( clip )  
			transitions.append( isTransition )
			starts.append( start )
			ends.append( end )
			alignments.append( alignment )
			in_adjustments.append( 0.0 )

		
		# Find the transition clips and check how they should be applied
		for i, clip in enumerate(track_info["clip_list"]):

			if transitions[i]:
				# defermine on which side(s) the clip should be applied the fix

				applyLeft = False
				applyRight = False
							
				if i > 0 and ends[i-1] == -1:
					applyLeft = True

				if i < len( starts )-1 and starts[i+1] == -1:
					applyRight = True
					
				# Compute a transiton time matching the determine the transition alignment 
				transitionTime = 0
				
				if alignments[i] == "center":
					transitionTime = float(int((ends[i]+starts[i])/2))				
				elif alignments[i] == "start-black" or alignments[i] == "start":
					transitionTime = starts[i]
				elif alignments[i] == "end-black" or alignments[i] == "end":
					transitionTime = ends[i]
				elif applyLeft and applyRight:
					transitionTime = float(int((ends[i]+starts[i])/2))
				elif applyLeft:
					transitionTime = ends[i]
				elif applyRight:				
					transitionTime = starts[i]

				# apply computed transition time to prev and next clips
				if applyLeft:
					ends[i-1] = transitionTime
				if applyRight:				
					starts[i+1] = transitionTime
					in_adjustments[i+1] = transitionTime - starts[i]



		# Read the clips (without the transitions)					
		for i, clip in enumerate(track_info["clip_list"]):
			if not transitions[i]:
				# we got a shot
				
				shot = self._readClip(clip, isVideo, starts[i], ends[i], in_adjustments[i] )
				# TODO: make sure trackNum and shot -determineTrack return the
				# same number!
				if isVideo:
					cmds.setAttr((shot + ".track"), int(track_info["trackNumber"]))
					cmds.shotTrack(shot, lock=locked)
				else:
					cmds.setAttr((shot + ".order"), trackNum)


	
	def _getTransitionInfo( self, clip ):
		clip_info = self.translator.getClip(clip)

		isTransition = clip_info.get("transition", False )
		start = float( clip_info.get("start", -1) )
		end = float( clip_info.get("end", -1) )

		alignment = ""
		if isTransition:
			alignment = clip_info.get("alignment", "" ).lower()
			
		return isTransition, start, end, alignment

	def _readClip(self, clip, isVideo, start, end, in_adjustment ):
		# TODO: ensure that we don't already have a shot with
		# the same shot name in the scene
		# TODO: ensure that the rate associated with the clip 
		# is the same as the rate of the whole sequence. Can
		# Maya support playback of different shots at different
		# rates? (I'm guessing no)
		# TODO: figure out how the naming should work. Should the
		# shot/audio node's name also match the "name" specified in
		# the EDL?

		if start == -1:
			self.logger.warning("Importer._readClip, start parameter == -1, clip not loaded")
			return

		if end == -1:
			self.logger.warning("Importer._readClip, end parameter == -1, clip not loaded")
			return

		clip_info = self.translator.getClip(clip)

		# Ensure that clip frame rate matches sequence frame rate
		self._checkFrameRates(clip, clip_info)

		clipIn = float(clip_info.get("in", 0))
		clipIn += in_adjustment

		clipNode = None

		
		clip_name = clip_info.get("name", "")
		# Note: The XML file could be utf-8, but Maya's nodes and attrs cannot be unicode.
		# So only use the name if it's valid
		try:
			clip_name = clip_name.encode("ascii")
		except:
			self.translator.logger.warning("Clip name contains multi-byte characters, using default name")
			clip_name = ""

		clipObjectName = _getValidClipObjectName( clip_name, isVideo )

		if isVideo:
			clipNode = cmds.shot(clipObjectName)

			adjustedEnd = float(end)
			adjustedEnd -= 1			#Final frame in editorial is always exclusive bug 342715
			

			cmds.shot(	clipNode, 
						e=1, 
						shotName=clip_name,
						sequenceStartTime=start,
						sequenceEndTime=adjustedEnd,
						clipZeroOffset=clipIn,
						startTime=start,			# Make Maya start/end the same as
						endTime=adjustedEnd,		# sequence start/end. Maya sequenceStart/end is not transoorted through EDL
						mute=(clip_info.get("enabled",True) == False) )

			# create a custom camera
			# TODO: write out camera info as meta-data, perhaps??
			cameraNodes = cmds.camera(name=(clipNode + "Camera"))
			cmds.shot(clipNode, e=1, currentCamera=cameraNodes[0])

		else:
			clipNode = cmds.createNode("audio", name=clipObjectName)
			
			cmds.sequenceManager( attachSequencerAudio = clipNode )
			
			cmds.sound( clipNode,
						e=1,
						offset=start,
						sourceStart=clipIn,
						sourceEnd= float(clip_info.get("out", 1)),
						endTime = end,
						mute=(clip_info.get("enabled",True) == False))

		# Store the minimum frame of the sequence
		if self.minFrameInFile is None or start < self.minFrameInFile:
			self.minFrameInFile = start

		file_elem = clip_info.get("file", None)
		if file_elem is not None:
			file_info = self.translator.getFile(file_elem)

			# Ensure that file frame rate matches sequence frame rate
			self._checkFrameRates(file_elem, file_info)

			# TODO: convert from pathurl to an abs path that maya knows how to read
			# Or, just use the file-name and assume it's in the Maya project?
			if "pathurl" in file_info:
				if isVideo:
					# query the frameCount. If this raises an error, it could be because 
					# the movie format is not supported on this platform
					try:
						frameCount = cmds.movieInfo(file_info["pathurl"], frameCount=1)[0]
					except:
						self.translator.logger.warning("Could not open video file %s. File could be corrupt, or movie format is not supported on this platform" % file_info["pathurl"])
						frameCount = 0

					video_height = file_info.get("height", None)
					if video_height is not None:
						cmds.setAttr( (clipNode + ".hResolution"), int(video_height))					
					video_width = file_info.get("width", None)
					if video_width is not None:
						cmds.setAttr( (clipNode + ".wResolution"), int(video_width))	

					cmds.shot(clipNode, e=1, clip=file_info["pathurl"])

					cmds.setAttr( (clipNode + ".clipDuration"), frameCount)
					cmds.setAttr( (clipNode + ".clipValid"), 1)
					cmds.setAttr( (clipNode + ".clipScale"), 1) #FCP Speed Effect not supported yet
					
				else:
					try:
						cmds.sound(clipNode, e=1, file=file_info["pathurl"])
					except:
						self.translator.logger.warning("Could not open audio file %s. File not found, or audio format not supported" % file_info["pathurl"])
		self.clip_dict[clip] = clipNode
		return clipNode


# Methods used by the Export class
def getShotsResolution():
	"""
	Returns the video resolution of the sequencer if all the shots have the same resolution 
	Otherwise it returns False, 0, 0
	"""

	shots = cmds.ls(type="shot")

	if len( shots ) > 0:
		
		width = cmds.getAttr( shots[0] + ".wResolution")
		height = cmds.getAttr( shots[0] + ".hResolution")
			
		for shot in shots:
			shotWidth = cmds.getAttr( shot + ".wResolution")
			shotHeight = cmds.getAttr( shot + ".hResolution")
				
			if width != shotWidth or height != shotHeight:
				return False, 0, 0
		
		return True, width, height
	else:
		return False, 0, 0
		
		
def getTimeCode():
	
	# temporarely report the mayaStartTime to the productionstartTime
	startFrame = int( cmds.timeCode( q=1, mayaStartFrame=1 ))
	hourBackup = int(cmds.timeCode( q=1, productionStartHour=1 ))
	minuteBackup = int(cmds.timeCode( q=1, productionStartMinute=1 ))
	secondBackup = int(cmds.timeCode( q=1, productionStartSecond=1 ))
	frameBackup = int(cmds.timeCode( q=1, productionStartFrame=1 ))
	newFrame = frameBackup-startFrame
	cmds.timeCode( e=1, productionStartHour=hourBackup, productionStartMinute = minuteBackup, productionStartSecond = secondBackup, productionStartFrame = newFrame )
	
	# Extract prodution timecode
	hour = cmds.timeCode( q=1, productionStartHour=1 )
	minute = cmds.timeCode( q=1, productionStartMinute=1 )
	second = cmds.timeCode( q=1, productionStartSecond=1 )
	frame = cmds.timeCode( q=1, productionStartFrame=1 )

	# restore original timecode values
	cmds.timeCode( e=1, productionStartHour=hourBackup, productionStartMinute = minuteBackup, productionStartSecond = secondBackup, productionStartFrame = frameBackup )
		
	timeCodeStr = '%02d:%02d:%02d:%02d' % ( hour, minute, second, frame )
		
	return timeCodeStr


def videoClipCompare( a, b ):
	startA = float( cmds.shot(a, q=1, sequenceStartTime=1))
	startB = float( cmds.shot(b, q=1, sequenceStartTime=1))
		
	return int( startA - startB )

		
def audioClipCompare( a, b ):
	startA = float( cmds.sound(a, q=1, offset=1))
	startB = float( cmds.sound(b, q=1, offset=1))
		
	return int( startA - startB )

class Exporter(ImportExport):
	def __init__(self):
		ImportExport.__init__(self)

		# <track num> : [list of shot/audio nodes on given track],
		self.shotNodes = {}
		self.audioNodes = {}
		
		self.allowPlayblast = True
	
	def setAllowPlayblast(self, allow):
		"""
		If true, will re-playblast of all shots whose clips are out of date
		or non-existent.
		"""
		self.allowPlayblast = allow 

	def doIt(self, fileName):
		ext = os.path.splitext(fileName)[-1]
		if ext.lower() == ".xml":
			self.translator = FCP(fileName)
		
		if self.translator is None:
			self._closeLoggingHandlers()
			raise Exception("Could not find translator for EDL file: %s" % fileName)
	
		self._setupLoggingHandlers()	
		
		# record first and last sequence frames
		firstSeqFrame = None
		lastSeqFrame = None

		# get a list of all shot nodes
		shots = cmds.ls(type="shot")
		for shot in shots:
			track = cmds.getAttr(shot + ".track")
			if track not in self.shotNodes:
				self.shotNodes[track] = [shot]
			else:
				self.shotNodes[track].append(shot)

			first = cmds.getAttr(shot + ".sequenceStartFrame")
			last = cmds.getAttr(shot + ".sequenceEndFrame")
			if firstSeqFrame is None or first < firstSeqFrame:
				firstSeqFrame = first
			if lastSeqFrame is None or last > lastSeqFrame:
				lastSeqFrame = last

			# Playblast the shot if it is out of sync or there is
			# no clip. Or if image plane exists, but is hidden (i.e.
			# assume that the Maya animation has changed)
			if self.allowPlayblast and (cmds.shot(shot, q=1, clipSyncState=1) != 1 or 
			   float(cmds.shot(shot, q=1, clipOpacity=1)) <= 0 ):
				doMel("performPlayblastShot(0, \"" + shot + "\")")

		# TODO: take into account audio's first/last frames too when
		# gather all the audio nodes
		sounds = cmds.ls(type="audio")
		for audio in sounds:
			track = cmds.getAttr(audio + ".order")
			self.audioNodes.setdefault(track, []).append(audio)
	
		# gather sequence-specific information
		sceneName = os.path.basename(cmds.file(q=1, loc=1))
		fps = cmds.currentUnit(q=1, time=1)

		self.seq_info = { "name": os.path.splitext(sceneName)[0] }
		self.seq_info["duration"] = (lastSeqFrame + 1 - firstSeqFrame)
		self.seq_info["framerate"] = [k for k, v in mayaFrameRates.iteritems() if v == fps][0]
		self.seq_info["timecode"] = getTimeCode()
		
		seq_elem = self.translator.writeSequence(self.seq_info)

		# write video resolution (format)
		hasCommonRes, width, height = getShotsResolution()

		if hasCommonRes:
			self.translator.writeFormat( seq_elem, width, height )

		# write video tracks
		trackNumbers = sorted(self.shotNodes.iterkeys())

		# Write tracks in reverse order to respect EDL eval order
		trackNumbers.reverse()
		
		for trackNum in trackNumbers:
			self._writeTrack(seq_elem, True, self.shotNodes[trackNum], trackNum)

		# write audio tracks
		trackNumbers = sorted(self.audioNodes.iterkeys())
		for trackNum in trackNumbers:
			self._writeTrack(seq_elem, False, self.audioNodes[trackNum], trackNum)
			
		self.translator.writeToFile()
		self._closeLoggingHandlers()

	def _writeTrack(self, seq_elem, isVideo, nodeList, trackNumber):
		"""
		Write the video/audio track. nodeList is a list of all shot/audio nodes in
		the track.
		"""
		track_info = {"type" : ("audio", "video")[isVideo] }
		
		numLocked = 0
		numEnabled = 0
		
		sortedNodeList = nodeList
		
		if isVideo:
			sortedNodeList.sort( videoClipCompare )
		else:
			sortedNodeList.sort( audioClipCompare )
		
		for clip in sortedNodeList:
			if isVideo:
				numLocked = numLocked + int(cmds.shot(clip, q=1, lock=1))
				numEnabled = numEnabled + int(not cmds.shot(clip, q=1, mute=1))
			else:
				numEnabled = numEnabled + int(not cmds.sound(clip, q=1, mute=1))

		track_info["locked"] = (numLocked == len(nodeList))
		track_info["enabled"] = (numEnabled == len(nodeList))
		track_info["trackNumber"] = trackNumber
        
		track_elem = self.translator.writeTrack(seq_elem, track_info)

		for clip in sortedNodeList:
			self._writeClip(track_elem, isVideo, clip)
	
	def _writeClip(self, track_elem, isVideo, clip):
		
		# Note: we'll make the clip name and id the same as the maya node-name
		# used for linking of audio and video
		clip_info = { "name" : clip, "id" : clip }

		if isVideo:
			seqStartTime = cmds.shot(clip, q=1, sequenceStartTime=1)
			clip_info["duration"] = cmds.shot(clip, q=1, sequenceDuration=1)
			clip_info["start"] = seqStartTime
			
			# Final frame in editorial is always exclusive (bug 342715), but it
			# is not in Maya, so we must add 1 at the end here when exporting
			seqEndTime = cmds.shot(clip, q=1, sequenceEndTime=1) + 1 
			clip_info["end"] = seqEndTime
			clip_info["enabled"] = not cmds.shot(clip, q=1, mute=1)
			
			inTime = cmds.shot(clip, q=1, clipZeroOffset=1)
			clip_info["in"] = inTime
			clip_info["out"] = inTime + seqEndTime - seqStartTime
			
			# TODO: pre/post hold
			
		else:
			seqOffset = cmds.sound(clip, q=1, offset=1)
			silence = float(cmds.getAttr((clip + ".silence")))
			mediaIn = cmds.sound(clip, q=1, sourceStart=1)
			mediaOut = cmds.sound(clip, q=1, sourceEnd=1)
			clip_info["start"] = (seqOffset + silence)
			clip_info["end"] = seqOffset + silence + mediaOut - mediaIn
			clip_info["in"] = mediaIn
			clip_info["out"] = mediaOut
			clip_info["duration"] = mediaOut - mediaIn
			clip_info["enabled"] = not cmds.sound(clip, q=1, mute=1)

		clip_elem = self.translator.writeClip(track_elem, clip_info)

		# Note: we won't be able to open this up unless we have a file.
		# So even if there's no file, create a dummy one
		file_info = { "name":clip }

		if isVideo:
			imagePlane = cmds.shot(clip, q=1, clip=1)
			if imagePlane is not None:
				try:
					# Using Maya API to get absolute path for the image plane media
					node = _nameToNode( imagePlane )
					file_info["pathurl"] = OpenMayaRender.MRenderUtil().exactImagePlaneFileName( node )
				except:
					file_info["pathurl"] = cmds.getAttr(imagePlane + ".imageName")				
				file_info["duration"] = cmds.shot( clip, q=1, clipDuration=1 )
		else:
			file_info["pathurl"] = cmds.sound(clip, q=1, file=1)
			file_info["duration"] = cmds.sound(clip, q=1, length=1)
		
		file_elem = self.translator.writeFile(clip_elem, file_info)



def doImport(fileName, useStartFrameOverride, startFrame):
	"""
	Imports the specified file using the EDL Importer class.
	"""
	importer = Importer();
	if useStartFrameOverride:
		importer.setStartFrameOverride(startFrame)
	try:
		importer.doIt(fileName)
	except:
		pass
	del importer
	
def doExport(fileName, allowPlayblast):
	"""
	Exports the Maya sequence using the EDL Exporter class.
	"""
	exporter = Exporter()
	exporter.setAllowPlayblast(allowPlayblast)
	exporter.doIt(fileName)
	del exporter
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
