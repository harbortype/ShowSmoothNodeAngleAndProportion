# encoding: utf-8
from __future__ import division, print_function, unicode_literals

###########################################################################################################
#
#
#	Reporter Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from math import degrees, hypot, atan2, cos, sin, radians, floor

class showSmoothNodeAngleAndProportion(ReporterPlugin):

	def settings(self):
		self.menuName = u'Smooth Node Angle and Proportion'
		self.thisMenuTitle = {"name": u"%s:" % self.menuName, "action": None }
		self.masterIds = []
		NSUserDefaults.standardUserDefaults().registerDefaults_({
				"com.harbortype.showSmoothNodeAngleAndProportion.showRatio": 0
			})


	def conditionalContextMenus(self):
		return [
		{
			'name': Glyphs.localize({
				'en': u"Show Smooth Node Angle and Proportion:",
				}), 
			'action': None,
		},
		{
			'name': Glyphs.localize({
				'en': u"Show Ratio Instead of Percentages", 
				}), 
			'action': self.toggleRatio,
			'state': Glyphs.defaults[ "com.harbortype.showSmoothNodeAngleAndProportion.showRatio" ],
		},
		]

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
		
		except:
			NSLog(traceback.format_exc())


	def toggleRatio(self):
		self.toggleSetting("showRatio")


	def toggleSetting(self, prefName):
		pref = "com.harbortype.showSmoothNodeAngleAndProportion.%s" % prefName
		oldSetting = bool(Glyphs.defaults[pref])
		Glyphs.defaults[pref] = int(not oldSetting)
		self.refreshView()


	def refreshView(self):
		try:
			Glyphs = NSApplication.sharedApplication()
			currentTabView = Glyphs.font.currentTab
			if currentTabView:
				currentTabView.graphicView().setNeedsDisplay_(True)
		except:
			pass



	def getHandleSize(self):
		""" Get the handle size in scale """
		handleSizes = (5, 8, 12)
		handleSizeIndex = Glyphs.handleSize 
		handleSize = handleSizes[handleSizeIndex] * self.getScale() ** 0.1 # scaled diameter
		return handleSize


	def getMasterIDs(self, layer):
		""" Get the masters and special layers IDs """
		masterIds = set()
		glyph = layer.parent
		for lyr in glyph.layers:
			if lyr.isSpecialLayer or lyr.layerId == lyr.associatedMasterId:
				masterIds.add(lyr.layerId)
		return list(masterIds)


	def getAngle(self, p1, p2):
		""" Calculates the angle between two points """
		dx, dy = p2.x - p1.x, p2.y - p1.y
		angle = degrees(atan2(dy, dx))
		angle = round(angle, 1)
		return angle


	def compatibleAngles(self, glyph, p, n):
		# Check for compatibility against all masters and special layers
		angles = []
		for masterId in self.masterIds:
			layer = glyph.layers[masterId]
			# Find the current base node and the coordinates of its surrounding nodes
			try:
				# GLYPHS 3:
				currentPath = layer.shapes[p]
			except:
				# GLYPHS 2:
				currentPath = layer.paths[p]
			if currentPath:
				nodeCount = len(currentPath.nodes)
				currentNode = currentPath.nodes[n]
				if currentNode:
					pos1 = currentPath.nodes[(n-1)%nodeCount].position # faster than node.prevNode
					pos2 = currentPath.nodes[(n+1)%nodeCount].position # faster than node.nextNode
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


	def compatibleProportions(self, glyph, p, n, originalHypot):
		# Check for compatibility against all masters and special layers
		compatibility = []
		for masterId in self.masterIds:
			layer = glyph.layers[masterId]
			# Find the current base node and its surrounding nodes
			try:
				# GLYPHS 3:
				currentPath = layer.shapes[p]
			except:
				# GLYPHS 2:
				currentPath = layer.paths[p]
			if currentPath:
				currentNode = currentPath.nodes[n]
				if currentNode:
					offcurveNodes = [currentNode.prevNode, currentNode.nextNode]
					# Calculate the hypotenuses
					hypotenuses = []
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = currentNode.position
						pos2 = offcurve.position
						hypotenuses.append(hypot(pos1.x - pos2.x , pos1.y - pos2.y))
					# Compare the proportions of one of the hypotenuses
					factor = 100 / (hypotenuses[0] + hypotenuses[1])
					originalFactor = 100 / (originalHypot[0] + originalHypot[1])
					proportion1 = factor * hypotenuses[0]
					proportion2 = originalFactor * originalHypot[0]
					# Check if the percentages are compatible
					roundError = 0.5
					if proportion1 >= proportion2 - roundError and proportion1 <= proportion2 + roundError:
						compatibility.append(True)
					else:
						compatibility.append(False)
		# If there are incompatible proportions, return False
		if False in compatibility:
			return False
		return True


	def getLabelPosition(self, nodePosition, angle, panelSize, offset=30, angleOffset=0.0):
		""" Calculates the position of the label """
		x, y = nodePosition
		w, h = panelSize
		normal = angle + angleOffset
		dx = cos(radians(normal)) * offset
		dy = sin(radians(normal)) * offset
		return NSPoint(x+dx-w/2, y+dy-h/2)


	def drawRoundedRectangleForStringAtPosition(self, string, center, fontsize, handleAngle, isAngle=False, compatible=False, angleOffset=0.0):
		""" Adapted from Stem Thickness by Rafał Buchner """
		layer = Glyphs.font.selectedLayers[0]
		scale = self.getScale()
		scaledSize = fontsize / scale
		width = len(string) / scaledSize
		margin = 2
		x, y = center
		x = round(x*2)*0.5
		y = round(y*2)*0.5

		# Set colors
		textColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, .75)
		if not layer.parent.mastersCompatible or layer.layerId not in self.masterIds or len(self.masterIds) == 1:
			# If masters are not compatible, or if it is not a special layer
			NSColor.colorWithCalibratedRed_green_blue_alpha_(.7, .7, .7, .5).set() # medium gray
		elif compatible == True:
			# If angle or proportion is the same
			NSColor.colorWithCalibratedRed_green_blue_alpha_(.9, .9, .9, .5).set() # light gray
		else:
			# If angle or proportion is NOT the same
			NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .9, .4, .7).set() # yellow

		# Configure text label
		
		fontAttributes = {
			NSFontAttributeName: NSFont.labelFontOfSize_(scaledSize),
			NSForegroundColorAttributeName: textColor
		}
		displayText = NSAttributedString.alloc().initWithString_attributes_(string, fontAttributes)
		textSize = displayText.size()
		textWidth = textSize.width*1.2 + margin
		textHeight = textSize.height*1.1 + margin*0.5
		
		# Draw rounded rectangle
		panel = NSRect()
		panel.size = NSSize(textWidth, textHeight)
		if angleOffset != 0.0:
			panel.origin = self.getLabelPosition(center, handleAngle, panel.size, offset=30/scale**0.9, angleOffset=angleOffset)
		else:
			panel.origin = NSPoint(
				x-floor(textSize.width) / 2-margin*1.5, 
				y-floor(textSize.height) / 2-margin)
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, textHeight * 0.3, textHeight * 0.3).fill()
		
		# Draw text label
		panelCenter = NSPoint(panel.origin.x+panel.size.width*0.5, panel.origin.y+panel.size.height*0.5)
		displayText.drawAtPoint_alignment_(panelCenter, 4)
		

	def foreground(self, layer=None):
		"""
		Display angle and proportion if one node is selected
		"""
		if layer:
			scale = self.getScale()
			glyph = layer.parent
			if len(layer.selection) == 1:
				selectedNode = layer.selection[0]
				if not isinstance(selectedNode, GSNode):
					return
				nextNode = selectedNode.nextNode
				if selectedNode.type is OFFCURVE: # finding the next oncurve node
					if nextNode.type != OFFCURVE:
						node = selectedNode.nextNode
						prevNode = selectedNode
						nextNode = node.nextNode
					else:
						node = selectedNode.prevNode
						nextNode = selectedNode
						prevNode = node.prevNode
				else:
					node = selectedNode
					prevNode = selectedNode.prevNode
			
				if node.smooth:
					path = node.parent
					try:
						# GLYPHS 3
						p = layer.indexOfObjectInShapes_(path)
					except:
						# GLYPHS 2
						p = layer.indexOfPath_(path)
					n = node.index
					hypotenuses = []
					offcurveNodes = (node.prevNode, node.nextNode)
				
					# Calculate the hypotenuses
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = node.position
						pos2 = offcurve.position
						hypotenuses.append(hypot(pos1.x-pos2.x , pos1.y-pos2.y))
					# Check if handles are compatible
					compatibleProportions = self.compatibleProportions(glyph, p, n, hypotenuses)
				
					# Check if angles are compatible
					pos1 = prevNode.position
					pos2 = nextNode.position
					angle = self.getAngle(pos1, pos2)
					compatibleAngles = self.compatibleAngles(glyph, p, n)

					# Calculate and draw the ratio
					if Glyphs.boolDefaults["com.harbortype.showSmoothNodeAngleAndProportion.showRatio"]:
						ratio = round(hypotenuses[0]/hypotenuses[1], 3)
						labelPosition = NSPoint(node.position.x , node.position.y)
						self.drawRoundedRectangleForStringAtPosition(u"%s" % format(ratio, '.3f'), labelPosition, 10, angle, compatible=compatibleProportions, angleOffset=270)
					# Or calculate and draw the percentages
					else:
						factor = 100 / (hypotenuses[0] + hypotenuses[1])
						for i, offcurve in enumerate(offcurveNodes):
							percent = round(hypotenuses[i] * factor, 1)
							pos1 = node.position
							pos2 = offcurve.position
							labelPosition = NSPoint(pos1.x + (pos2.x-pos1.x)/2 , pos1.y + (pos2.y-pos1.y)/2)
							self.drawRoundedRectangleForStringAtPosition(u"%s%%" % str(percent), labelPosition, 10, angle, compatible=compatibleProportions)

					# Draw the angle if it different than 0.0 or if it is not compatible
					if angle not in (-90.0, 0.0, 90.0, 180.0) or not compatibleAngles:
						labelPosition = NSPoint(node.position.x , node.position.y)
						self.drawRoundedRectangleForStringAtPosition(u"%s°" % str(angle % 180), labelPosition, 10, angle, isAngle=True, compatible=compatibleAngles, angleOffset=90)


	def background(self, layer=None):
		"""
		Highlight the nodes that may produce kinks
		"""
		if layer:
			# color and size for highlight:
			NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .9, .4, .7).set() # yellow
			scale = self.getScale()
			handleSize = self.getHandleSize()
			width = handleSize*2/scale
			
			
			self.masterIds = self.getMasterIDs(layer)
			glyph = layer.parent
			if len(self.masterIds) <= 1:
				return
			if layer.layerId not in self.masterIds:
				return
			if not layer.paths:
				return
			
			# step through paths:
			try:
				# GLYPHS 3:
				paths = layer.shapes
			except:
				# GLYPHS 2:
				paths = layer.paths
			for p, path in enumerate(paths):
				if type(path) is GSPath:
					nodeCount = len(path.nodes)
					for n, node in enumerate(path.nodes):
						if node.smooth and node.type is not OFFCURVE:
							hypotenuses = []
							prevNode = path.nodes[(n-1)%nodeCount] # faster than node.prevNode
							nextNode = path.nodes[(n+1)%nodeCount] # faster than node.nextNode
							offcurveNodes = (prevNode, nextNode)
					
							# Calculate the hypotenuses
							for i, offcurve in enumerate(offcurveNodes):
								pos1 = node.position
								pos2 = offcurve.position
								hypotenuses.append(hypot(pos1.x - pos2.x , pos1.y - pos2.y))
					
							# Calculate the percentages
							factor = 100 / (hypotenuses[0] + hypotenuses[1])
							compatibleProportions = self.compatibleProportions(glyph, p, n, hypotenuses)
					
							# Get the angle
							pos1 = prevNode.position
							pos2 = nextNode.position
							angle = self.getAngle(pos1, pos2)
							compatibleAngles = self.compatibleAngles(glyph, p, n)
					
							if not compatibleAngles and not compatibleProportions:
								# draw the yellow disk behind node
								highlightArea = NSRect()
								highlightArea.size = NSSize(width, width)
								highlightArea.origin = NSPoint(node.x-width/2, node.y-width/2)
								NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(highlightArea, width*0.5, width*0.5).fill()

	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
