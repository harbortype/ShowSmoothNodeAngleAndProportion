# encoding: utf-8
from __future__ import division, print_function, unicode_literals
import objc
import math
import traceback
from GlyphsApp import Glyphs, GSNode, OFFCURVE, subtractPoints
from GlyphsApp.plugins import ReporterPlugin, setUpMenuHelper
from AppKit import NSMenuItem, NSColor, NSString, NSFont, NSBezierPath, NSLog, NSPoint, NSRect, NSSize, NSFontAttributeName, NSForegroundColorAttributeName

###########################################################################################################
#
#
# Reporter Plugin
#
# Read the docs:
# https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

TEXT_COLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, .75)
COLOR_INCOMPATIBLE = NSColor.colorWithCalibratedRed_green_blue_alpha_(.6, .65, .8, .5)
COLOR_ORANGE = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .65, .65, .6)
COLOR_YELLOW = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .9, .4, .7)
COLOR_YELLOW_LINE = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .65, .0, .4)
COLOR_GRAY = NSColor.colorWithCalibratedRed_green_blue_alpha_(.9, .9, .9, .5)


class showKinks(ReporterPlugin):

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Kinks',
			'pt': u'Ângulo e Proporção dos Nós',
		})
		self.thisMenuTitle = {"name": u"%s:" % self.menuName, "action": None}
		self.layerIds = []
		Glyphs.registerDefaults({
			"com.harbortype.showKinks.showRatio": 0,
			"com.harbortype.showKinks.showOtherMasters": 0,
		})

	@objc.python_method
	def conditionalContextMenus(self):
		return [
			{
				'name': Glyphs.localize({
					'en': u"Show Kinks:",
					'pt': u"Exibir Ângulo e Proporção dos Nós:",
				}),
				'action': None,
			},
			{
				'name': Glyphs.localize({
					'en': u"Show angles of other masters",
					'pt': u"Exibir ângulos das outras masters",
				}),
				'action': self.toggleMasters_,
				'state': Glyphs.defaults["com.harbortype.showKinks.showOtherMasters"],
			},
			{
				'name': Glyphs.localize({
					'en': u"Show ratio instead of percentages",
					'pt': u"Exibir razão ao invés de porcentagens",
				}),
				'action': self.toggleRatio_,
				'state': Glyphs.defaults["com.harbortype.showKinks.showRatio"],
			},
		]

	@objc.python_method
	def addMenuItemsForEvent_toMenu_(self, event, contextMenu):
		'''
		The event can tell you where the user had clicked.
		'''
		try:
			if self.generalContextMenus:
				setUpMenuHelper(contextMenu, self.generalContextMenus, self)

			newSeparator = NSMenuItem.separatorItem()
			contextMenu.addItem_(newSeparator)

			contextMenus = self.conditionalContextMenus()
			if contextMenus:
				setUpMenuHelper(contextMenu, contextMenus, self)

		except Exception as e:
			NSLog(traceback.format_exc(), e)

	def toggleRatio_(self, sender):
		self.toggleSetting("showRatio")

	def toggleMasters_(self, sender):
		self.toggleSetting("showOtherMasters")

	@objc.python_method
	def toggleSetting(self, prefName):
		pref = "com.harbortype.showKinks.%s" % prefName
		oldSetting = bool(Glyphs.defaults[pref])
		Glyphs.defaults[pref] = int(not oldSetting)
		self.refreshView()

	@objc.python_method
	def refreshView(self):
		try:
			currentTabView = Glyphs.font.currentTab
			if currentTabView:
				currentTabView.graphicView().setNeedsDisplay_(True)
		except:
			pass

	@objc.python_method
	def getAxisTag(self, axis):
		"""Returns the axis tag."""
		if Glyphs.versionNumber < 3.0:
			return axis["Tag"]
		else:
			return axis.axisTag

	@objc.python_method
	def getLayerAxesValues(self, thisLayer):
		"""Returns the layer axes values as a list of floats."""
		if thisLayer.isBraceLayer():
			# brace layer
			axesDict = thisLayer.attributes["coordinates"]
			if not axesDict:
				return []
			orderedAxesDict = dict()
			for axisId in self.axesIds:
				orderedAxesDict[axisId] = axesDict[axisId]
			layerValues = list(orderedAxesDict.values())
		elif thisLayer.isBracketLayer():
			# bracket layer
			# TODO
			layerValues = []
		else:
			# normal layer (master)
			font = thisLayer.parent.parent
			masterLayer = font.masters[thisLayer.associatedMasterId]
			layerValues = list(masterLayer.axes)
		return layerValues

	@objc.python_method
	def getHandleSize(self):
		""" Get the handle size in scale """
		handleSizes = (5, 8, 12)
		handleSizeIndex = Glyphs.handleSize
		handleSize = handleSizes[handleSizeIndex] * self.getScale() ** 0.1  # scaled diameter
		return handleSize

	@objc.python_method
	def matchIgnoredAxes(self, layer, activeMaster):
		""" Checks if the current layer should be checked against the active master considering the ignored axes parameter """
		activeMasterCoords = activeMaster.axes
		layerCoords = self.getLayerAxesValues(layer)
		if not layerCoords:
			return
		axesIndexes = [self.axesTags.index(x) for x in self.ignoreAxes]
		axesMatch = all([layerCoords[i] == activeMasterCoords[i] for i in axesIndexes])
		return axesMatch

	@objc.python_method
	def getMasterIDs(self, layer):
		""" Get the masters and special layers IDs """
		masterIds = set()
		glyph = layer.parent
		font = glyph.parent
		self.ignoreAxes = []
		if "Ignore Kinks Along Axes" in font.customParameters:
			ignoreParam = font.customParameters["Ignore Kinks Along Axes"]
			if ignoreParam:
				self.ignoreAxes = [x.strip() for x in ignoreParam.split(",")]
				for x in range(len(self.ignoreAxes)-1, -1, -1):
					if self.ignoreAxes[x] not in self.axesTags:
						del self.ignoreAxes[x]

		activeMaster = layer.master
		for lyr in glyph.layers:
			# Process master layers
			if lyr.layerId == lyr.associatedMasterId:
				if not self.ignoreAxes:
					masterIds.add(lyr.layerId)
					continue

				# If any axes should be ignored, discard layers that
				# do not share the same coordinates on those axes
				if self.matchIgnoredAxes(lyr, activeMaster):
					masterIds.add(lyr.layerId)

			# Process brace layers
			elif lyr.isSpecialLayer:
				if not self.ignoreAxes:
					masterIds.add(lyr.layerId)
					continue

				if lyr.isBraceLayer():
					if self.matchIgnoredAxes(lyr, activeMaster):
						masterIds.add(lyr.layerId)

		return list(masterIds)

	@objc.python_method
	def getAngle(self, p1, p2):
		""" Calculates the angle between two points """
		dx, dy = p2.x - p1.x, p2.y - p1.y
		angle = math.degrees(math.atan2(dy, dx))
		angle = round(angle, 1)
		return angle

	@objc.python_method
	def getPrevNextNodes(self, currentPath, nodeIndex):
		prevNode = currentPath.nodes[nodeIndex - 1]
		try:
			nextNode = currentPath.nodes[nodeIndex + 1]
		except IndexError:
			nextNode = currentPath.nodes[0]
		return prevNode, nextNode

	@objc.python_method
	def compatibleAngles(self, glyph, pathIndex, nodeIndex):
		# Exit if masters not compatible
		if not glyph.mastersCompatibleForLayerIds_(self.layerIds):
			return
		# Check for compatibility against all masters and special layers
		angles = []
		for masterId in self.layerIds:
			layer = glyph.layers[masterId]
			# Find the current base node and the coordinates of its surrounding nodes
			try:
				currentPath = layer.paths[pathIndex]
			except:
				continue
			if currentPath:
				currentNode = currentPath.nodes[nodeIndex]
				if currentNode:
					prevNode, nextNode = self.getPrevNextNodes(currentPath, nodeIndex)
					pos1 = prevNode.position
					pos2 = nextNode.position
					# Calculate the angle between the surrounding nodes
					# (we are assuming the base node is smooth)
					angles.append(self.getAngle(pos1, pos2))
		# Check if the angles are compatible
		minAngle = min(angles)
		maxAngle = max(angles)
		maxDiff = 1.0
		if maxAngle - minAngle > maxDiff:
			return False
		return True

	@objc.python_method
	def compatibleProportions(self, glyph, pathIndex, nodeIndex, originalHypot):
		# Exit if masters not compatible
		if not glyph.mastersCompatibleForLayerIds_(self.layerIds):
			return None
		# Check for compatibility against all masters and special layers

		for masterId in self.layerIds:
			layer = glyph.layers[masterId]
			# Find the current base node and its surrounding nodes
			try:
				currentPath = layer.paths[pathIndex]
			except:
				continue
			if currentPath:
				currentNode = currentPath.nodes[nodeIndex]
				if currentNode:
					prevNode, nextNode = self.getPrevNextNodes(currentPath, nodeIndex)
					offcurveNodes = [prevNode, nextNode]
					# Calculate the hypotenuses
					hypotenuses = []
					nodePos = currentNode.position
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = nodePos
						pos2 = offcurve.position
						hypotenuses.append(math.hypot(pos1.x - pos2.x, pos1.y - pos2.y))
					# Compare the proportions of one of the hypotenuses
					factor = 100 / (hypotenuses[0] + hypotenuses[1])
					originalFactor = 100 / (originalHypot[0] + originalHypot[1])
					proportion1 = factor * hypotenuses[0]
					proportion2 = originalFactor * originalHypot[0]
					# Check if the percentages are compatible
					roundError = 0.5
					if not (proportion1 >= proportion2 - roundError and proportion1 <= proportion2 + roundError):
						return False
		return True

	@objc.python_method
	def getLabelPosition(self, nodePosition, angle, panelSize, offset=30, angleOffset=0.0):
		""" Calculates the position of the label """
		x, y = nodePosition
		w, h = panelSize
		normal = angle + angleOffset
		dx = math.cos(math.radians(normal)) * offset
		dy = math.sin(math.radians(normal)) * offset
		return NSPoint(x + dx - w / 2, y + dy - h / 2)

	@objc.python_method
	def drawRoundedRectangleForStringAtPosition(self, string, center, fontsize, handleAngle, isAngle=False, compatible=False, angleOffset=0.0):
		""" Adapted from Stem Thickness by Rafał Buchner """
		layer = Glyphs.font.selectedLayers[0]
		scale = self.getScale()
		# handleSize = self.getHandleSize()

		scaledSize = fontsize / scale
		# width = len(string) * scaledSize
		margin = 2

		origin = self.activePosition()
		center = NSPoint(center.x * scale + origin[0], center.y * scale + origin[1])
		x, y = center

		# Set colors
		textColor = TEXT_COLOR
		if compatible:
			# If angle or proportion is the same
			COLOR_GRAY.set()
		elif not layer.parent.mastersCompatibleForLayerIds_(self.layerIds):
			# If masters are not compatible, or if it is not a special layer
			COLOR_INCOMPATIBLE.set()
			# print("Layers are incompatible.")
		elif layer.layerId not in self.layerIds:
			# Not a master layer nor special layer
			COLOR_INCOMPATIBLE.set()
			# print("Layer should not be considered.")
		elif len(self.layerIds) == 1:
			# If is single master
			COLOR_INCOMPATIBLE.set()
		elif layer.parent.parent.customParameters["Ignore Kinks Along Axes"]:
			# If angle or proportion is NOT the same and some axes are being ignored
			COLOR_ORANGE.set()
		else:
			# If angle or proportion is NOT the same
			COLOR_YELLOW.set()

		# Configure text label
		string = NSString.stringWithString_(string)
		attributes = {
			NSFontAttributeName: NSFont.systemFontOfSize_(fontsize / scale),
			NSForegroundColorAttributeName: textColor
		}
		textSize = string.sizeWithAttributes_(attributes)

		# Draw rounded rectangle
		panel = NSRect()
		panel.size = NSSize(math.floor(textSize.width) + margin * 2 * 1.5, textSize.height + margin * 1.5)
		if angleOffset != 0.0:
			panel.origin = self.getLabelPosition(center, handleAngle, panel.size, angleOffset=angleOffset)
		else:
			panel.origin = NSPoint(
				x - math.floor(textSize.width) / 2 - margin * 1.5,
				y - textSize.height / 2 - margin)
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, scaledSize * 0.5, scaledSize * 0.5).fill()

		# Draw text label
		panelCenter = NSPoint(
			panel.origin.x + panel.size.width / 2,
			panel.origin.y + panel.size.height / 2)
		self.drawTextAtPoint(string, panelCenter, fontsize, align="center", fontColor=textColor)

	@objc.python_method
	def drawBackgroundHandles(self, layer, pathIndex, nodeIndex, scale):
		# radius = 2
		glyph = layer.parent
		currentId = layer.layerId
		currentPath = layer.paths[pathIndex]
		currentNode = currentPath.nodes[nodeIndex]
		currentPos = currentNode.position
		origin = self.activePosition()
		basePosition = NSPoint(currentPos.x * scale + origin.x, currentPos.y * scale + origin.y)
		COLOR_YELLOW_LINE.set()
		for masterId in self.layerIds:
			# Don't draw the current layer
			if masterId == currentId:
				continue
			# Get the nodes
			masterLayer = glyph.layers[masterId]
			masterPath = masterLayer.paths[pathIndex]
			baseNode = masterPath.nodes[nodeIndex]
			prevNode, nextNode = self.getPrevNextNodes(currentPath, nodeIndex)
			basePos = baseNode.position
			for offcurve in [nextNode, prevNode]:
				# Calculate the position delta to the base node
				diff = subtractPoints(offcurve.position, basePos)
				offcurvePosition = NSPoint((currentPos.x + diff.x) * scale + origin.x, (currentPos.y + diff.y) * scale + origin.y)
				# Draw line
				line = NSBezierPath.bezierPath()
				line.setLineWidth_(1)
				line.moveToPoint_(basePosition)
				line.lineToPoint_(offcurvePosition)
				line.stroke()
				# Draw nodes
				# panel = NSRect()
				# panel.size = NSSize(radius * 2, radius * 2)
				# panel.origin = NSPoint((x+dx) * scale + origin.x - radius, (y+dy) * scale + origin.y - radius)
				# NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, radius, radius).stroke()

	@objc.python_method
	def foregroundInViewCoords(self, layer=None):
		""" Draw stuff on the screen """
		layer = self.activeLayer()
		if layer:
			scale = self.getScale()
			glyph = layer.parent
			if len(layer.selection) == 1:
				selectedNode = layer.selection[0]
				if not isinstance(selectedNode, GSNode):
					return
				selectedPath = selectedNode.parent
				nodeIndex = selectedNode.index
				prevNode, nextNode = self.getPrevNextNodes(selectedPath, nodeIndex)

				if selectedNode.type is OFFCURVE:  # finding the next oncurve node
					if nextNode.type != OFFCURVE:
						node = nextNode
					else:
						node = prevNode
					prevNode, nextNode = self.getPrevNextNodes(selectedPath, node.index)
				else:
					node = selectedNode

				if node.smooth:
					path = node.parent
					try:
						pathIndex = layer.indexOfObjectInShapes_(path)
					except:
						pathIndex = layer.indexOfPath_(path)
					nodeIndex = node.index
					hypotenuses = []
					prevNode, nextNode = self.getPrevNextNodes(path, nodeIndex)
					offcurveNodes = [prevNode, nextNode]
					nodePos = node.position
					# Calculate the hypotenuses
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = nodePos
						pos2 = offcurve.position
						hypotenuses.append(math.hypot(pos1.x - pos2.x, pos1.y - pos2.y))
					# Check if handles are compatible
					compatibleProportions = self.compatibleProportions(glyph, pathIndex, nodeIndex, hypotenuses)

					# Check if angles are compatible
					pos1 = prevNode.position
					pos2 = nextNode.position
					angle = self.getAngle(pos1, pos2)
					compatibleAngles = self.compatibleAngles(glyph, pathIndex, nodeIndex)

					# Calculate and draw the ratio
					if Glyphs.boolDefaults["com.harbortype.showKinks.showRatio"]:
						ratio = round(hypotenuses[0] / hypotenuses[1], 3)
						labelPosition = nodePos
						self.drawRoundedRectangleForStringAtPosition(u"%.2f" % ratio, labelPosition, 10 * scale, angle, compatible=compatibleProportions, angleOffset=270)

					# Or calculate and draw the percentages
					else:
						factor = 100 / (hypotenuses[0] + hypotenuses[1])
						for i, offcurve in enumerate(offcurveNodes):
							percent = round(hypotenuses[i] * factor, 1)
							pos1 = nodePos
							pos2 = offcurve.position
							labelPosition = NSPoint(pos1.x + (pos2.x - pos1.x) / 2, pos1.y + (pos2.y - pos1.y) / 2)
							self.drawRoundedRectangleForStringAtPosition(u"%s%%" % str(percent), labelPosition, 10 * scale, angle, compatible=compatibleProportions)

					# Draw the angle if it different than 0.0 or if it is not compatible
					angleExceptions = [-90.0, 0.0, 90.0, 180.0]
					if angle not in angleExceptions or not compatibleAngles:
						labelPosition = nodePos
						self.drawRoundedRectangleForStringAtPosition(u"%.1f°" % (angle % 180), labelPosition, 10 * scale, angle, isAngle=True, compatible=compatibleAngles, angleOffset=90)

	@objc.python_method
	def backgroundInViewCoords(self, layer=None):
		""" Mark the nodes that may produce kinks """

		layer = self.activeLayer()
		if not layer:
			return
		font = layer.parent.parent
		self.axesTags = []
		self.axesIds = []
		for axis in font.axes:
			self.axesTags.append(self.getAxisTag(axis))
			self.axesIds.append(axis.axisId)
		self.layerIds = self.getMasterIDs(layer)
		scale = self.getScale()
		handleSize = self.getHandleSize()
		glyph = layer.parent
		if len(self.layerIds) <= 1:
			return
		if layer.layerId not in self.layerIds:
			return
		if not glyph.mastersCompatibleForLayerIds_(self.layerIds):
			return
		if not layer.paths:
			return

		origin = self.activePosition()
		selectedNode = None
		# Draw handles from other masters
		if Glyphs.boolDefaults["com.harbortype.showKinks.showOtherMasters"]:
			if len(layer.selection) == 1:
				selectedNode = layer.selection[0]
				if not (isinstance(selectedNode, GSNode) and selectedNode.type is not OFFCURVE):
					selectedNode = None

		for pathIndex, path in enumerate(layer.paths):
			for nodeIndex, node in enumerate(path.nodes):
				if node.smooth and node.type is not OFFCURVE:
					hypotenuses = []
					prevNode, nextNode = self.getPrevNextNodes(path, nodeIndex)
					offcurveNodes = [prevNode, nextNode]

					# Draw handles from other masters
					if selectedNode and (selectedNode in offcurveNodes or node == selectedNode):
						self.drawBackgroundHandles(layer, pathIndex, nodeIndex, scale)
					nodePos = node.position
					# Calculate the hypotenuses
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = nodePos
						pos2 = offcurve.position
						hypotenuses.append(math.hypot(pos1.x - pos2.x, pos1.y - pos2.y))

					# Calculate the percentages
					# factor = 100 / (hypotenuses[0] + hypotenuses[1])
					compatibleProportions = self.compatibleProportions(glyph, pathIndex, nodeIndex, hypotenuses)

					# Get the angle
					pos1 = prevNode.position
					pos2 = nextNode.position
					# angle = self.getAngle(pos1, pos2)
					compatibleAngles = self.compatibleAngles(glyph, pathIndex, nodeIndex)

					if not compatibleAngles and not compatibleProportions:
						# scaledSize = fontsize / scale
						width = handleSize * 2
						margin = 0
						center = NSPoint(nodePos.x * scale + origin.x, nodePos.y * scale + origin.y)
						x, y = center

						# Draw circle behind the node
						panel = NSRect()
						panel.size = NSSize(width + margin * 2, width + margin * 2)
						panel.origin = NSPoint(x - width / 2 - margin, y - width / 2 - margin)
						if self.ignoreAxes:
							COLOR_ORANGE.set()
						else:
							COLOR_YELLOW.set()
						NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, (width + margin * 2) * 0.5, (width + margin * 2) * 0.5).fill()

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
