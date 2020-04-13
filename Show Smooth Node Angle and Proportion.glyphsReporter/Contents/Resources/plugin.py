# encoding: utf-8
from __future__ import division, print_function, unicode_literals
import objc, math, traceback
from GlyphsApp import *
from GlyphsApp.plugins import *
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




class showSmoothNodeAngleAndProportion(ReporterPlugin):

	@objc.python_method 
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Smooth Node Angle and Proportion',
			'pt': u'Ângulo e Proporção dos Nós',

		})
		self.thisMenuTitle = {"name": u"%s:" % self.menuName, "action": None }
		self.masterIds = []
		NSUserDefaults.standardUserDefaults().registerDefaults_({
				"com.harbortype.showSmoothNodeAngleAndProportion.showRatio": 0,
				"com.harbortype.showSmoothNodeAngleAndProportion.showOtherMasters": 0,
			})


	@objc.python_method 
	def conditionalContextMenus(self):
		return [
		{
			'name': Glyphs.localize({
				'en': u"Show Smooth Node Angle and Proportion:",
				'pt': u"Exibir Ângulo e Proporção dos Nós:",
				}), 
			'action': None,
		},
		{
			'name': Glyphs.localize({
				'en': u"Show angles of other masters", 
				'pt': u"Exibir ângulos das outras masters", 
				}), 
			'action': self.toggleMasters,
			'state': Glyphs.defaults[ "com.harbortype.showSmoothNodeAngleAndProportion.showOtherMasters" ],
		},
		{
			'name': Glyphs.localize({
				'en': u"Show ratio instead of percentages", 
				'pt': u"Exibir razão ao invés de porcentagens", 
				}), 
			'action': self.toggleRatio,
			'state': Glyphs.defaults[ "com.harbortype.showSmoothNodeAngleAndProportion.showRatio" ],
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
			NSLog(traceback.format_exc())


	@objc.python_method 
	def toggleRatio(self):
		self.toggleSetting("showRatio")


	@objc.python_method 
	def toggleMasters(self):
		self.toggleSetting("showOtherMasters")


	@objc.python_method 
	def toggleSetting(self, prefName):
		pref = "com.harbortype.showSmoothNodeAngleAndProportion.%s" % prefName
		oldSetting = bool(Glyphs.defaults[pref])
		Glyphs.defaults[pref] = int(not oldSetting)
		self.refreshView()


	@objc.python_method 
	def refreshView(self):
		try:
			Glyphs = NSApplication.sharedApplication()
			currentTabView = Glyphs.font.currentTab
			if currentTabView:
				currentTabView.graphicView().setNeedsDisplay_(True)
		except Exception as e:
			pass



	@objc.python_method 
	def getHandleSize(self):
		""" Get the handle size in scale """
		handleSizes = (5, 8, 12)
		handleSizeIndex = Glyphs.handleSize 
		handleSize = handleSizes[handleSizeIndex] * self.getScale() ** 0.1 # scaled diameter
		return handleSize


	@objc.python_method 
	def getMasterIDs(self, layer):
		""" Get the masters and special layers IDs """
		masterIds = set()
		glyph = layer.parent
		for lyr in glyph.layers:
			if lyr.isSpecialLayer or lyr.layerId == lyr.associatedMasterId:
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
	def compatibleAngles(self, glyph, p, n):
		# Exit if masters not compatible
		if not glyph.mastersCompatible:
			return
		# Check for compatibility against all masters and special layers
		angles = []
		for masterId in self.masterIds:
			layer = glyph.layers[masterId]
			# Find the current base node and the coordinates of its surrounding nodes
			currentPath = layer.paths[p]
			if currentPath:
				currentNode = currentPath.nodes[n]
				if currentNode:
					pos1 = currentNode.prevNode.position
					pos2 = currentNode.nextNode.position
					# Calculate the angle between the surrounding nodes 
					# (we are assuming the base node is smooth)
					angles.append (self.getAngle(pos1, pos2))
		# Check if the angles are compatible
		minAngle = min(angles)
		maxAngle = max(angles)
		maxDiff = 1.0
		if maxAngle - minAngle > maxDiff:
			return False
		return True


	@objc.python_method 
	def compatibleProportions(self, glyph, p, n, originalHypot):
		# Exit if masters not compatible
		if not glyph.mastersCompatible:
			return
		# Check for compatibility against all masters and special layers
		compatibility = []
		for masterId in self.masterIds:
			layer = glyph.layers[masterId]
			# Find the current base node and its surrounding nodes
			try:
				currentPath = layer.shapes[p]
			except:
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
						hypotenuses.append(math.hypot(pos1.x - pos2.x , pos1.y - pos2.y))
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


	@objc.python_method 
	def getLabelPosition(self, nodePosition, angle, panelSize, offset=30, angleOffset=0.0):
		""" Calculates the position of the label """
		x, y = nodePosition
		w, h = panelSize
		normal = angle + angleOffset
		dx = math.cos(math.radians(normal)) * offset
		dy = math.sin(math.radians(normal)) * offset
		return NSPoint(x+dx-w/2, y+dy-h/2)


	@objc.python_method 
	def drawRoundedRectangleForStringAtPosition(self, string, center, fontsize, handleAngle, isAngle=False, compatible=False, angleOffset=0.0):
		""" Adapted from Stem Thickness by Rafał Buchner """
		layer = Glyphs.font.selectedLayers[0]
		scale = self.getScale()
		handleSize = self.getHandleSize()
		
		scaledSize = fontsize / scale
		width = len(string) * scaledSize
		margin = 2
		currentTab = Glyphs.font.currentTab
		origin = currentTab.selectedLayerOrigin
		center = NSPoint(center.x * scale + origin[0] , center.y * scale + origin[1])
		x, y = center

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
		string = NSString.stringWithString_(string)
		attributes = {
			NSFontAttributeName:            NSFont.systemFontOfSize_(fontsize/scale),
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
				x-math.floor(textSize.width) / 2 - margin * 1.5, 
				y-textSize.height / 2-margin)
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, scaledSize * 0.5, scaledSize * 0.5).fill()
		
		# Draw text label
		panelCenter = NSPoint(
			panel.origin.x + panel.size.width/2,
			panel.origin.y + panel.size.height/2)
		self.drawTextAtPoint(string, panelCenter, fontsize, align="center", fontColor=textColor)


	@objc.python_method 
	def drawBackgroundHandles(self, layer, p, n, scale):
		radius = 2
		glyph = layer.parent
		currentLayer = layer.layerId
		currentNode = layer.paths[p].nodes[n]
		x = currentNode.position.x
		y = currentNode.position.y
		currentTab = Glyphs.font.currentTab
		origin = currentTab.selectedLayerOrigin
		basePosition = NSPoint( x * scale + origin[0], y * scale + origin[1] )
		for masterLayer in self.masterIds:
			# Don't draw the current layer
			if masterLayer == currentLayer:
				continue
			# Get the nodes
			baseNode = glyph.layers[masterLayer].paths[p].nodes[n]
			nextNode = baseNode.nextNode
			prevNode = baseNode.prevNode
			for offcurve in [nextNode, prevNode]:
				# Calculate the position delta to the base node
				dx = offcurve.position.x - baseNode.position.x
				dy = offcurve.position.y - baseNode.position.y
				offcurvePosition = NSPoint( (x+dx) * scale + origin[0], (y+dy) * scale + origin[1] )
				# Draw line
				NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .65, .0, .4).set() # orange
				line = NSBezierPath.bezierPath()
				line.setLineWidth_(1)
				line.moveToPoint_(basePosition)
				line.lineToPoint_(offcurvePosition)
				line.stroke()
				# Draw nodes
				# panel = NSRect()
				# panel.size = NSSize(radius * 2 , radius * 2)
				# panel.origin = NSPoint( (x+dx) * scale + origin[0] - radius, (y+dy) * scale + origin[1] - radius )
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
				nextNode = selectedNode.nextNode
				prevNode = selectedNode.prevNode
				if selectedNode.type is OFFCURVE: # finding the next oncurve node
					if nextNode.type != OFFCURVE:
						node = nextNode
						prevNode = selectedNode
						nextNode = node.nextNode
					else:
						node = prevNode
						nextNode = selectedNode
						prevNode = node.prevNode
				else:
					node = selectedNode
			
				if node.smooth:
					path = node.parent
					try:
						p = layer.indexOfObjectInShapes_(path)
					except:
						p = layer.indexOfPath_(path)
					n = node.index
					hypotenuses = []
					offcurveNodes = [node.prevNode, node.nextNode]
				
					# Calculate the hypotenuses
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = node.position
						pos2 = offcurve.position
						hypotenuses.append(math.hypot(pos1.x - pos2.x , pos1.y - pos2.y))
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
						self.drawRoundedRectangleForStringAtPosition(u"%s" % format(ratio, '.3f'), labelPosition, 10 * scale, angle, compatible=compatibleProportions, angleOffset=270)
				
					# Or calculate and draw the percentages
					else:
						factor = 100 / (hypotenuses[0] + hypotenuses[1])
						for i, offcurve in enumerate(offcurveNodes):
							percent = round(hypotenuses[i] * factor, 1)
							pos1 = node.position
							pos2 = offcurve.position
							labelPosition = NSPoint(pos1.x + (pos2.x - pos1.x) / 2 , pos1.y + (pos2.y - pos1.y) / 2)
							self.drawRoundedRectangleForStringAtPosition(u"%s%%" % str(percent), labelPosition, 10 * scale, angle, compatible=compatibleProportions)

					# Draw the angle if it different than 0.0 or if it is not compatible
					angleExceptions = [-90.0, 0.0, 90.0, 180.0]
					if angle not in angleExceptions or not compatibleAngles:
						labelPosition = NSPoint(node.position.x , node.position.y)
						self.drawRoundedRectangleForStringAtPosition(u"%s°" % str(angle % 180), labelPosition, 10 * scale, angle, isAngle=True, compatible=compatibleAngles, angleOffset=90)


	@objc.python_method 
	def backgroundInViewCoords(self, layer=None):
		""" Mark the nodes that may produce kinks """

		layer = Glyphs.font.selectedLayers[0]
		self.masterIds = self.getMasterIDs(layer)
		scale = self.getScale()
		handleSize = self.getHandleSize()
		glyph = layer.parent
		if len(self.masterIds) <= 1:
			return
		if layer.layerId not in self.masterIds:
			return
		if not glyph.mastersCompatible:
			return
		if not layer.paths:
			return
		
		for p, path in enumerate(layer.paths):
			for n, node in enumerate(path.nodes):
				if node.smooth and node.type is not OFFCURVE:
					hypotenuses = []
					prevNode = node.prevNode
					nextNode = node.nextNode
					offcurveNodes = [prevNode, nextNode]

					# Draw handles from other masters
					if Glyphs.boolDefaults["com.harbortype.showSmoothNodeAngleAndProportion.showOtherMasters"]:
						if len(layer.selection) == 1:
							selectedNode = layer.selection[0]
							if selectedNode in offcurveNodes or node == selectedNode:
								self.drawBackgroundHandles(layer, p, n, scale)
					
					# Calculate the hypotenuses
					for i, offcurve in enumerate(offcurveNodes):
						pos1 = node.position
						pos2 = offcurve.position
						hypotenuses.append(math.hypot(pos1.x - pos2.x , pos1.y - pos2.y))
					
					# Calculate the percentages
					factor = 100 / (hypotenuses[0] + hypotenuses[1])
					compatibleProportions = self.compatibleProportions(glyph, p, n, hypotenuses)
					
					# Get the angle
					pos1 = prevNode.position
					pos2 = nextNode.position
					angle = self.getAngle(pos1, pos2)
					compatibleAngles = self.compatibleAngles(glyph, p, n)
					
					if not compatibleAngles and not compatibleProportions:
						# scaledSize = fontsize / scale
						width = handleSize*2
						margin = 0
						currentTab = Glyphs.font.currentTab
						origin = currentTab.selectedLayerOrigin
						center = NSPoint(node.position.x * scale + origin[0] , node.position.y * scale + origin[1])
						x, y = center
						
						# Draw circle behind the node
						panel = NSRect()
						panel.size = NSSize(width + margin * 2 , width + margin * 2)
						panel.origin = NSPoint(x - width / 2 - margin, y - width / 2 - margin)
						NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .9, .4, .7).set() # yellow
						NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, (width + margin * 2) * 0.5, (width + margin * 2) * 0.5).fill()



	@objc.python_method 
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
