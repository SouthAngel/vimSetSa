
"""
This class will allow the read/write of Final Cut Pro XML files.
"""


from maya.app.edl.translator import *
import xml.etree.cElementTree as ET

def indent(elem, level=0):
	"""
	This is from ElementTree's Element Library. By default XML is written 
	in the compact form, with no whitespace. So we need to do the indenting
	ourselves to get human-readable XML
	"""
	i = "\n" + level*"  "
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + "  "
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for elem in elem:
			indent(elem, level+1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i

class FCP(Translator):

	def __init__(self, fileName):
		Translator.__init__(self, fileName)

		self.root = None
		self.sequence = None

		# Store master clip info. This is the clip information from the <bin>
		# section of an XML file. These clips/files will be accessed in the <sequence>
		# section by the id. The key will be the master clip id, the values are as 
		# follows:
		#
		# name = name of the clip
		# start = start frame of clip
		# end = end frame of clip
		# framerate = frames per second
		# duration = duration in frames
		# 
		# clipitems = list of <clipitem> elements (both audio and video)
		#
		self.master_clips = {}

		# save clip/file elements by id. Needed for linking of audio/video 
		# and referencing of master clips
		self.file_ids = {}
		self.clip_ids = {}

		# list of lists. Each nested list is a group of linked ids
		self.links = []

		# Element Tree objects do not store parent pointers. But we need access
		# to the parent to generate useful error messages with proper context. 
		# So store a mapping for each track/file/clip element to its parent Element.
		self.parent_pointers = {}

		# Current element being processed. Used for error reporting
		self.cur_elem = None
	
	def formatErrorElement(self, cur_elem):
		"""
		Format information about the current element that will be used in an error message.
		So we want the type of element (ex: file, clip etc) and the name/id.
		"""
		tagName = "name"
		tagValue = None

		if cur_elem is not None:
			tagValue = cur_elem.find(tagName)
			if tagValue is None:
				tagName = "id"
				tagValue = cur_elem.get("id")
			else:
				tagValue = tagValue.text

			if tagValue is None:
				if cur_elem in self.parent_pointers:
					return self.formatErrorElement(self.parent_pointers[cur_elem])
			else:
				return ("%s with %s '%s' " % (cur_elem.tag, tagName, tagValue))
			return "unknown %s element" % cur_elem.tag
			
		return "unknown element"

	def _getRate(self, rate_elem):
		"""
		Given a <rate> SubElement, return the frame rate
		"""
		if not ET.iselement(rate_elem) or rate_elem.tag != "rate":
			self.logger.warning("FCP._getRate must be passed a <rate> sub element")
			return 0
		
		# Final Cut Pro supports drop-frame formats as follows. If the <ntsc> tag is FALSE, it's
		# a whole-number frame rate. If it's TRUE, we have a decimal frame rate, so we apply a 
		# multiplier to the timebase. This table lists the supported rates:
		# http://developer.apple.com/mac/library/documentation/AppleApplications/Reference/FinalCutPro_XML/FrameRate/FrameRate.html#//apple_ref/doc/uid/TP30001158-TPXREF103
		#
		multiplier = 1.0
		timebase = 0 
		for item in rate_elem:
			if item.tag == "ntsc":
				if item.text.upper() == "TRUE":
					multipier = 0.999
			elif item.tag == "timebase":
				timebase = int(item.text)

		if timebase == 0:
			self.logger.error("timebase was not specified for rate in %s" % self.formatErrorElement(self.cur_elem) )

		return (multiplier * timebase)
	
	def _getTimecode(self, timecode_elem):
		"""
		Given a timecode sub element (which is returned by getSequence or getClip or getFile),
		return the following information:

		framerate 	= in frames per second
		string		= timecode format. ex: "smpte"
		"""
		if not ET.iselement(timecode_elem) or timecode_elem.tag != "timecode":
			self.logger.error("FCP.getTimecode must be given an <timecode> element")
			return {}

		self.cur_elem = timecode_elem
		timecode_info = {}

		for item in timecode_elem:
			if item.tag == "rate":
				timecode_info["framerate"] = self._getRate(item)
			elif item.tag == "string":
				timecode_info[item.tag] = item.text

		return timecode_info

	
	def _getSampleCharacteristics(self, sample_elem):
		"""
		Given a <samplecharacteristics> SubElement, return dictionary with the
		following information (if appropriate):

		width			= width of video
		height			= height of video
		depth			= audio bit depth
		samplerate		= audio sample rate
		"""
		if not ET.iselement(sample_elem) or sample_elem.tag != "samplecharacteristics":
			self.logger.error("FCP._getSampleCharacteristics must be given a <samplecharacteristics> item")
			return {}

		#TODO: there are lots of other tags in samplecharacteristics, like:
		# anamorphic, pixelaspectration,fielddominance,rate etc. Which ones
		# do we care about enough to return?
		sample_info = {}
		for item in sample_elem:
			if (item.tag == "width" or item.tag == "height" or 
			   item.tag == "depth" or item.tag == "samplerate"):
				sample_info[item.tag] = item.text

		return sample_info

	def _getFormat(self, format_elem):
		"""
		Given a <format> SubElement, return a dictionary with relevant info.
		Note that format only has one possible child: samplecharacteristics.
		But <samplecharacteristics> tags can be embedded in <video> or <audio>
		tags as well.
		"""
		if not ET.iselement(format_elem) or format_elem.tag != "format":
			self.logger.warning("FCP._getFormat must be given a <format> item")
			return {}

		for item in format_elem:
			if item.tag == "samplecharacteristics":
				return self._getSampleCharacteristics(item)
		return {}

	def _isValidFileElement(self, file_elem):
		"""
		Check to make sure the file element is valid. This means
		we must have either a <name> or <pathurl> tag and the value
		should not be empty
		"""

		path_elem = file_elem.find("pathurl")
		if path_elem is not None and len(path_elem.text) > 0:
			return True

		name_elem = file_elem.find("name")
		if name_elem is not None and len(name_elem.text) > 0:
			return True
		
		return False

	def readFromFile(self):
		"""
		Reads XML file and populates an ElementTree hierarchy
		"""
		if not os.path.exists(self.fileName):
			self.logger.error("%s file does not exist" % self.fileName)
		elif self.root is not None:
			self.logger.warning("%s has already been read" % self.fileName)
		else:
			tree = ET.parse(self.fileName)
			self.root = tree.getroot()

			# pre-parse the <bin> tags for any master clips
			self.getMasterClips()

	def getMasterClips(self):
		"""
		Read the <bin> tag and all master clip and file information. Will
		populate the self.master_clips dictionary.
		"""
		bin_elem = self.root.find("bin")
		if bin_elem is None:
			return

		children_elem = bin_elem.find("children")
		if children_elem is None:
			return

		if children_elem is None:
			return

		for clip in children_elem:
			if clip.tag == "clip":
				# process the master clip
				id = clip.get("id", None)
				if id is not None:
					self.master_clips[id] = { "clipitems":[] } 
					for item in clip:
						if item.tag in ("name", "duration", "start", "end"):
							self.master_clips[id][item.tag] = item.text
						elif item.tag == "rate":
							self.master_clips[id]["framerate"] = self._getRate(item)
						elif item.tag == "media":
							for media_type in item:
								if media_type.tag in ("audio", "video"):
									for track in media_type:
										# note: audio tags can have in/out in addition to track as children
										if track.tag == "track":
											track_info = self.getTrack(track)
											if "clip_list" in track_info:
												self.master_clips[id]["clipitems"].extend( track_info["clip_list"] )
									# end for track
							# end for media_type
					# end for item

					# For each clipitem, pull all the files into the
					# global file_ids dictionary
					for clipitem in self.master_clips[id]["clipitems"]:
						clip_info = self.getClip(clipitem)
						if "file" in clip_info:
							file_elem = clip_info["file"]
							fid = file_elem.get("id", None)
							if fid is not None and fid not in self.file_ids:
								self.file_ids[fid] = file_elem
								

	def getSequence(self):
		"""
		Read the sequence information from a Final Cut Pro XML hierarchy.
		Assumes that XML has already been parsed with readFromFile method.

		Returns dictionary containing the following:

		name			= name of the sequence
		duration 		= duration in frames
		framerate 		= in frames per second
		timecode		= timecode string
		video_tracks 	= list of video track SubElements. Use getTrack to
						  read the contents
		audio_tracks	= list of audio track SubElements. use getTrack to
						  read the contents
		"""

		if self.root is None:
			self.logger.error("No root for FCP XML hierarchy found. Could not getSequence")
			return {}

		if self.sequence is None:
			for item in self.root:
				if( item.tag == "sequence"):
					self.sequence = item
					break

		if self.sequence is None:
			self.logger.error("No sequence found in %s" % self.fileName)

		self.cur_elem = self.sequence
		seq_info = {}

		for item in self.sequence:
			if item.tag == "name" or item.tag == "duration":
				seq_info[item.tag] = item.text
			elif item.tag == "rate":
				seq_info["framerate"] = self._getRate(item)
			elif item.tag == "timecode":
				timecode_info = self._getTimecode(item)
			
				if "string" in timecode_info:
					seq_info["timecode"] = timecode_info["string"]
			
			elif item.tag == "media":
				for media in item:
					track_list = []
					if media.tag == "video" or media.tag == "audio":
						for child in media:
							if child.tag == "track":
								track_list.append(child)
								self.parent_pointers[child] = self.sequence
							elif child.tag == "format":
								seq_info.update( self._getFormat(child) )
						if media.tag == "video":
							seq_info["video_tracks"] = track_list
						else:
							seq_info["audio_tracks"] = track_list
					elif media.tag == "format":
						seq_info.update( self._getFormat(media) )
		return seq_info

	def getTrack(self, track_elem):
		"""
		Given a track element (which is returned by getSequence), read the
		relevant information.

		Returns dictionary containing the following:

		locked 		= True/False
		enabled 	= True/False
		width		= width in pixels (if specified)
		height		= height in pixels (if specified)

		clip_list 	= list of clipitem SubElements that are a part of this track.
					  To read data from the clips, use getClip
		"""
		
		if not ET.iselement(track_elem) or track_elem.tag != "track":
			self.logger.error("FCP.getTrack must be given a <track> item")
			return {}

		self.cur_elem = track_elem
		track_info = { "clip_list" : [] }

		for item in track_elem:
			if item.tag == "clipitem" or item.tag == "transitionitem":
				track_info["clip_list"].append(item)
				self.parent_pointers[item] = track_elem
			elif item.tag == "locked":
				# TODO: determine if FCP XML is case-sensitive about its boolean values
				track_info["locked"] = (item.text.upper() == "TRUE")
			elif item.tag == "enabled":
				track_info["enabled"] = (item.text.upper() == "TRUE")
			elif item.tag == "format":
				track_info.update( self._getFormat(item) )
			elif item.tag == "trackNumber":
				track_info["trackNumber"] = item.text
		return track_info
	
	def getClip(self, clip_elem):
		"""
		Given a clip element or transition item (which is returned b getTrack), return a dictionary with the
		following information:
		id			= id of the clip. Will be used for linking, referencing clips in the 
					  browser etc.
		name 		= name of the clip item
		duration	= in frames
		enabled 	= True/False
		start/end 	= define placement of clip in the sequence
		in/out		= define start/end frames of the clip in source media
		file		= eTree SubElement for the <file> tag. Use getFile method to read contents
		transition  = indicates if the clip is a transition, will be True is the clip is a transition item= True
		alignment	= define the placement of a transition, not present for clips
					  according to FCP/XML doc, valid values are center, start, end, start-black and end-black
		"""
		if not ET.iselement(clip_elem) or ( clip_elem.tag != "clipitem" and clip_elem.tag != "transitionitem"):
			self.logger.warning("FCP.getClip must be called on a <clipitem> or a <transitionitem> element")
			return

		self.cur_elem = clip_elem
		link_index = None

		id = clip_elem.get("id", None)
		if id is not None:
			self.clip_ids[id] = clip_elem

		clip_info = { "id" : id }

		if clip_elem.tag == "transitionitem":
			clip_info["transition"] = True
		else:
			clip_info["transition"] = False

		for item in clip_elem:
			if item.tag in ("name", "duration", "start", "end", "in", "out", "alignment" ):
			   clip_info[item.tag] = item.text
			elif item.tag == "timecode":
				# TODO: remember to fill this in!
				pass
			elif item.tag == "masterclipid":
				# Load the master clip info. Choose which parts to
				# pull from the master clip. We'll start with the
				# framerate.
				# TODO: determine which framerate should take precedence.
				# The one on the masterclip or the one on the clipitem
				if item.text not in self.master_clips:
					self.logger.warning("masterclipid %s not found" % item.text)
				elif "framerate" in self.master_clips[item.text]:
					clip_info["framerate"] = self.master_clips[item.text]["framerate"]
			elif item.tag == "file":
				clip_info["file"] = item
				self.parent_pointers[item] = clip_elem
			elif item.tag == "enabled":
				clip_info["enabled"] = (item.text.upper() == "TRUE")
			elif item.tag == "rate" and "framerate" not in clip_info:
				clip_info["framerate"] = self._getRate(item) 
			elif item.tag == "link":
				# all links from this clip should be added to the same group?
				if link_index is None:
					link_index = len(self.links)
					self.links.append([])
				
				for child in item:
					if child.tag == "linkclipref":
						self.links[link_index].append(child.text)

		return clip_info

	def getFile(self, file_elem):
		"""
		Given a file element (returned by getClip), return a dictionary with the following
		information:

		id			= id of the clip. Can be used to reference a file that's already been
					  defined somewhere else
		name		= name of file
		pathurl 	= path to file (i.e. file://)

		"""
		if not ET.iselement(file_elem) or file_elem.tag != "file":
			self.logger.error("FCP.getFile must be called with a <file> element")
			return {}


		id = file_elem.get("id", None)
		if id is not None:
			# check if we're referencing a pre-defined file.
			# If not, add this to the list
			if id in self.file_ids and self._isValidFileElement(self.file_ids[id]):
				file_elem = self.file_ids[id] 
			else:
				self.file_ids[id] = file_elem
	
		self.cur_elem = file_elem 
		file_info = { "id" : id }

		for item in file_elem:
			if item.tag == "pathurl":
				path = item.text
				# FCP will sometimes tack on 'localhost', but the rest of the path
				# string is a valid full path. So try to strip that out first.
				path = path.replace("file://localhost", "", 1)

				# FCP spec says it can generate both file:/// and file://, but in practice, 
				# I have only been able to get file://. In fact, searching for file:/// 
				# strips away the leading "/" on Mac and Linux.
				path = path.replace("file://", "", 1)
				
				# Maya does not automaticaly replace %20 with spaces when dealing with file name
				# immediately replace these replacement characters 
				path = path.replace("%20", " ")

				file_info[item.tag] = path
			elif item.tag == "name" or item.tag == "duration":
				file_info[item.tag] = item.text
			elif item.tag == "rate":
				file_info["framerate"] = self._getRate(item)
			elif item.tag == "media":
				for type in item:
					if type.tag == "video" or type.tag == "audio":
						for child in type:
							if child.tag == "samplecharacteristics":
								file_info.update( self._getSampleCharacteristics(child) )
							elif child.tag == "format":
								# TODO: determine if this is possible, a <video><format> tag inside <file>
								file_info.update( self._getFormat(child) )

		if "pathurl" not in file_info and "name" not in file_info:
			self.logger.warning("Neither pathurl nor file name were specified for %s", self.formatErrorElement(self.cur_elem) )

		return file_info

	
	def getLinks(self):
		"""
		Return a list of dictionaries that map ids to elements.
		Each dict is a link group 
		"""
		link_info = []
		for group in self.links:
			# lookup each id in group in the clip dictionary
			dict = {}
			for id in group:
				if id in self.clip_ids:
					dict[id] = self.clip_ids[id]
			link_info.append(dict)
		return link_info

	def _writeRate(self, elem, rate):
		"""
		Adds a <rate> sub element to 'elem'
		"""

		rate_elem = ET.SubElement(elem, "rate")
		
		# The ntsc tag will only be true for decimal frame rates.
		# So check if we have a whole-number rate
		# Note: Maya currently does not support drop-frame rates
		# but we may extend it to do so in the future.
		ntsc = ("TRUE", "FALSE")[int(rate) == rate]
		ntsc_elem = ET.SubElement(rate_elem, "ntsc")
		ntsc_elem.text = ntsc

		timebase_elem = ET.SubElement(rate_elem, "timebase")
		timebase_elem.text = str(int(rate))

		return rate_elem

	def _writeTimeCode(self, elem, timeCode):
		"""
		Adds a <timecode> sub element to 'elem'
		"""

		timeCode_elem = ET.SubElement(elem, "timecode")
		
		string_elem = ET.SubElement(timeCode_elem, "string")
		string_elem.text = timeCode

		return timeCode_elem

	def writeToFile(self):
		"""
		Write the XML file in memory to disk
		"""
		if self.root is None:
			self.logger.error("Cannot write file, translator was not populated")
			return

		indent(self.root)
		xmlTree = ET.ElementTree(self.root)

		xmlTree.write(self.fileName, encoding="utf-8")	
		
	def writeSequence(self, seq_info):
		"""
		Write the sequence. We expect seq_info to contain the following information:

		name			= name of the sequence
		duration 		= duration in frames
		framerate 		= in frames per second
		timecode		= timecode of the sequence (optional)
		"""
		if self.root is not None:
			self.logger.error("%s has already been written" % self.fileName)
			return None

		self.root = ET.Element("xmeml", version="1.0")
		self.sequence = ET.SubElement(self.root, "sequence")
		
		for k, v in seq_info.iteritems():
			if k == "name" or k =="duration":
				elem = ET.SubElement(self.sequence, k)
				elem.text = str(v)

		# the timecode field requires that the framerate field gets writen first and 
		# just looping on the dictionary does not guarantied that consistence
		if "framerate" in seq_info:
			self._writeRate(self.sequence, seq_info["framerate"] )
			
			if "timecode" in seq_info:
				self._writeTimeCode( self.sequence, seq_info["timecode"] )

		return self.sequence

	def writeFormat(self, seq_elem, width, height ):
		"""
		Add a format element to the specified sequence. 
		"""

		if not ET.iselement(seq_elem) or seq_elem.tag != "sequence":
			self.logger.error("FCP.writeFormat must be passed a valid <sequence> element")
			return None
		
		media_elem = seq_elem.find("media")
		if media_elem is None:
			media_elem = ET.SubElement(seq_elem, "media")

		if media_elem is None:
			self.logger.error("Could not add <media> tag to sequence")
			return None

		video_elem = media_elem.find("video")
		
		if video_elem is None:
			video_elem = ET.SubElement( media_elem, "video")

		if video_elem is None:
			self.logger.error("Could not add <video> tag to media" )
			return None

		format_elem = ET.SubElement(video_elem, "format")

		if format_elem is None:
			self.logger.error("Could not add <format> tag to video" )
			return None
			
		sample_char_elem = ET.SubElement(format_elem, "samplecharacteristics")

		if sample_char_elem is None:
			self.logger.error("Could not add <samplecharacteristics> tag to format" )
			return None

		width_elem = ET.SubElement(sample_char_elem, "width" )
		width_elem.text = str(width)

		height_elem = ET.SubElement(sample_char_elem, "height" )
		height_elem.text = str(height)

		return format_elem

	
	def writeTrack(self, seq_elem, track_info):
		"""
		Add a track to the specified sequence. track_info must contain the following info:

		type		= "audio" or "video"
		name		= name of track
		locked 		= True/False
		enabled 	= True/False
		"""

		if not ET.iselement(seq_elem) or seq_elem.tag != "sequence":
			self.logger.error("FCP.writeTrack must be passed a valid <sequence> element")
			return None
		
		media_elem = seq_elem.find("media")
		if media_elem is None:
			media_elem = ET.SubElement(seq_elem, "media")

		if media_elem is None:
			self.logger.error("Could not add <media> tag to sequence")
			return None

		type_elem = None
		type = track_info.get("type", "video")
		type_elem = media_elem.find(type)
		if type_elem is None:
			type_elem = ET.SubElement(media_elem, type)

		if type_elem is None:
			self.logger.error("Could not add <%s> tag to sequence media" % type)
			return None

		track_elem = ET.SubElement(type_elem, "track")

		for k, v in track_info.iteritems():
			if k == "name":
				elem = ET.SubElement(track_elem, k)
				elem.text = v
			elif k == "locked" or k == "enabled":
				elem = ET.SubElement(track_elem, k)
				elem.text = ("FALSE", "TRUE")[v]
			elif k == "trackNumber":
				elem = ET.SubElement(track_elem, k)
				elem.text = str(v)

		return track_elem

	
	def writeClip(self, track_elem, clip_info):
		"""
		Add a clip to the specified track. clip_info must contain the following info:
		name 		= name of the clip item
		duration	= in frames
		enabled 	= True/False
		start/end 	= define placement of clip in the sequence
		in/out		= define start/end frames of the clip in source media
		"""

		if not ET.iselement(track_elem) or track_elem.tag != "track":
			self.logger.error("FCP.writeClip must be passed a valid <track> element")
			return None

		clip_elem = ET.SubElement(track_elem, "clipitem")

		for k, v in clip_info.iteritems():
			if k == "id":
				clip_elem.set("id", v)
			else:
				elem = ET.SubElement(clip_elem, k)
				elem.text = str(v)
		return clip_elem

	def writeFile(self, clip_elem, file_info):
		"""
		Add a file to the specified clip. file_info must contain the following:
		
		id					= used for linking of audio/video
		name or pathurl		= file name or absolute path to the location
		duration			= media length (sequence frames)
		"""

		if not ET.iselement(clip_elem) or clip_elem.tag != "clipitem":
			self.logger.error("FCP.writeFile must be passed a valid <clipitem> element")
			return None

		file_elem = ET.SubElement(clip_elem, "file")

		if "id" in file_info:
			file_elem.set("id", file_info["id"])

		for k, v in file_info.iteritems():
			elem = ET.SubElement(file_elem, k)
			if k == "pathurl":
				if not os.path.isabs(str(v)):
					self.logger.warning("FCP.writeFile must be given an absolute file path. Received: %s" % str(v))
				filename = v.replace( " ", "%20" )
				elem.text = "file://%s" % filename
			else:
				elem.text = str(v)

		return file_elem

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
