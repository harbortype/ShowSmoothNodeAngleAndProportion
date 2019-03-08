# encoding: utf-8

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

import objc, math
from GlyphsApp import *
from GlyphsApp.plugins import *

masterIds = []


class showKinkHelper(ReporterPlugin):

	def settings(self):
		self.menuName = Glyphs.localize({'en': u'Kink Helper'})


	def getHandleSize(self):
		""" Get the handle size in scale """
		handleSizes = (5, 8, 12)
		handleSizeIndex = Glyphs.handleSize 
		handleSize = handleSizes[handleSizeIndex]*self.getScale()**0.1 # scaled diameter
		return handleSize


	def getMasterIDs(self, layer):
		""" Get the masters and special layers IDs """
		global masterIds
		masterIds = []
		glyph = layer.parent
		font = glyph.parent
		for master in font.masters:
			masterIds.append( master.id )
		for lyr in glyph.layers:
			if lyr.isSpecialLayer:
				masterIds.append( lyr.layerId )
		return masterIds


	def getAngle(self, p1, p2):
		""" Calculates the angle between two points """
		dx, dy = p1.x - p2.x, p1.y - p2.y
		angle = math.degrees( math.atan2( dy, dx ) )
		angle = round( angle % 90, 1 )
		return angle


	def compatibleAngles(self, p, n, originalAngle):
		global masterIds
		currentLayer = Glyphs.font.selectedLayers[0]
		currentGlyph = currentLayer.parent
		# Check for compatibility against all masters and special layers
		angles = []
		for layer in currentGlyph.layers:
			if layer.layerId in masterIds:
				# Find the current base node and the coordinates of its surrounding nodes
				currentNode = layer.paths[p].nodes[n]
				pos1 = currentNode.prevNode.position
				pos2 = currentNode.nextNode.position
				# Calculate the angle between the surrounding nodes (we are assuming the base node is smooth)
				angles.append ( self.getAngle( pos1, pos2 ) )
		# Check if the angles are compatible
		minAngle = min(angles)
		maxAngle = max(angles)
		maxDiff = 1.0
		if maxAngle - minAngle > maxDiff:
			return False
		return True


	def compatibleProportions(self, p, n, originalHypot):
		global masterIds
		currentLayer = Glyphs.font.selectedLayers[0]
		currentGlyph = currentLayer.parent
		# Check for compatibility against all masters and special layers
		compatibility = []
		for layer in currentGlyph.layers:
			if layer.layerId in masterIds:
				# Find the current base node and its surrounding nodes
				currentNode = layer.paths[p].nodes[n]
				offcurveNodes = [ currentNode.prevNode, currentNode.nextNode ]
				# Calculate the hypotenuses
				hypotenuses = []
				for i, offcurve in enumerate( offcurveNodes ):
					pos1 = currentNode.position
					pos2 = offcurve.position
					hypotenuses.append( math.hypot( pos1.x - pos2.x , pos1.y - pos2.y ) )
				# Compare the proportions of one of the hypotenuses
				factor = 100 / ( hypotenuses[0] + hypotenuses[1] )
				originalFactor = 100 / ( originalHypot[0] + originalHypot[1] )
				proportion1 = factor * hypotenuses[0]
				proportion2 = originalFactor * originalHypot[0]
				# Check if the percentages are compatible
				roundError = 0.5
				if proportion1 >= proportion2 - roundError and proportion1 <= proportion2 + roundError:
					compatibility.append( True )
				else:
					compatibility.append( False )
		# If there are incompatible proportions, return False
		if False in compatibility:
			return False
		return True


	def drawRoundedRectangleForStringAtPosition(self, string, center, fontsize, isAngle=False, compatible=False ):
		""" Adapted from Stem Thickness by Rafał Buchner """
		global masterIds
		layer = Glyphs.font.selectedLayers[0]
		scale = self.getScale()
		handleSize = self.getHandleSize()
		
		scaledSize = fontsize / scale
		width = len(string) * scaledSize
		margin = 2
		currentTab = Glyphs.font.currentTab
		origin = currentTab.selectedLayerOrigin
		center = NSPoint( center.x * scale + origin[0] , center.y * scale + origin[1] )
		x, y = center

		# Set colors
		textColor = NSColor.colorWithCalibratedRed_green_blue_alpha_( 0,0,0,.75 )
		if not layer.parent.mastersCompatible or layer.layerId not in masterIds:
			# If masters are not compatible, or if it is not a special layer
			NSColor.colorWithCalibratedRed_green_blue_alpha_( .7,.7,.7,.5 ).set() # medium gray
		elif compatible == True:
			# If angle or proportion is the same
			NSColor.colorWithCalibratedRed_green_blue_alpha_( .9,.9,.9,.5 ).set() # light gray
		else:
			# If angle or proportion is NOT the same
			NSColor.colorWithCalibratedRed_green_blue_alpha_( 1,.9,.4,.7 ).set() # yellow

		# Configure text label
		string = NSString.stringWithString_(string)
		attributes = NSString.drawTextAttributes_( textColor )
		textSize = string.sizeWithAttributes_(attributes)
		
		# Draw rounded rectangle
		panel = NSRect()
		panel.size = NSSize( math.floor(textSize.width) + margin*2*1.5, textSize.height + margin*1.5 )
		if isAngle == True:
			panel.origin = NSPoint( 
				x-math.floor(textSize.width)/2-margin*1.5, 
				y-textSize.height/2-margin + textSize.height/2 + handleSize+4 )
		else:
			panel.origin = NSPoint( 
				x-math.floor(textSize.width)/2-margin*1.5, 
				y-textSize.height/2-margin )
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, scaledSize*0.5, scaledSize*0.5 ).fill()
		
		# Draw text label
		if isAngle == True:
			center = NSPoint( x, y + textSize.height/2 + handleSize+4 )
		self.drawTextAtPoint( string, center, fontsize, align="center", fontColor=textColor )
		

	def foregroundInViewCoords(self, layer):
		""" Draw stuff on the screen """
		global masterIds
		masterIds = self.getMasterIDs(layer)
		scale = self.getScale()
		if layer.paths and len(layer.selection) == 1:
			for p, path in enumerate( layer.paths ):
				for n, node in enumerate( path.nodes ):
					if node.smooth:
						if node.selected or node.nextNode.selected or node.prevNode.selected:
							hypotenuses = []
							offcurveNodes = [ node.prevNode, node.nextNode ]
							
							# Calculate the hypotenuses
							for i, offcurve in enumerate( offcurveNodes ):
								pos1 = node.position
								pos2 = offcurve.position
								hypotenuses.append( math.hypot( pos1.x - pos2.x , pos1.y - pos2.y ) )
							
							# Calculate the percentages
							factor = 100 / ( hypotenuses[0] + hypotenuses[1] )
							compatibleProportions = self.compatibleProportions( p, n, hypotenuses )
							# Draw the percentages
							for i, offcurve in enumerate( offcurveNodes ):
								percent = round( hypotenuses[i] * factor, 1 )
								pos1 = node.position
								pos2 = offcurve.position
								labelPosition = NSPoint( pos1.x + ( pos2.x - pos1.x ) / 2 , pos1.y + ( pos2.y - pos1.y ) / 2 )
								if offcurve.selected or node.selected:
									self.drawRoundedRectangleForStringAtPosition( u"%s%%" % str(percent), labelPosition, 8 * scale, compatible=compatibleProportions )

							# Draw the angle
							pos1 = node.prevNode.position
							pos2 = node.nextNode.position
							angle = self.getAngle( pos1, pos2 )
							
							compatibleAngles = self.compatibleAngles( p, n, angle )
							# Draw the angle if it different than 0.0 or if it is not compatible
							if angle != 0.0 or not compatibleAngles:
								labelPosition = NSPoint( node.position.x , node.position.y )
								self.drawRoundedRectangleForStringAtPosition( u"%s°" % str(angle), labelPosition, 8 * scale, isAngle=True, compatible=compatibleAngles )


	def backgroundInViewCoords(self, layer):
		""" Mark the nodes that may produce kinks """
		global masterIds
		masterIds = self.getMasterIDs(layer)
		scale = self.getScale()
		handleSize = self.getHandleSize()
		if len(masterIds) > 1:
			if layer.paths and layer.layerId in masterIds:
				for p, path in enumerate( layer.paths ):
					for n, node in enumerate( path.nodes ):
						if node.smooth:
							hypotenuses = []
							offcurveNodes = [ node.prevNode, node.nextNode ]
							
							# Calculate the hypotenuses
							for i, offcurve in enumerate( offcurveNodes ):
								pos1 = node.position
								pos2 = offcurve.position
								hypotenuses.append( math.hypot( pos1.x - pos2.x , pos1.y - pos2.y ) )
							
							# Calculate the percentages
							factor = 100 / ( hypotenuses[0] + hypotenuses[1] )
							compatibleProportions = self.compatibleProportions( p, n, hypotenuses )
								
							# Get the angle
							pos1 = node.prevNode.position
							pos2 = node.nextNode.position
							angle = self.getAngle( pos1, pos2 )
							compatibleAngles = self.compatibleAngles( p, n, angle )
							
							if not compatibleAngles and not compatibleProportions:
								# scaledSize = fontsize / scale
								width = handleSize*2
								margin = 0
								currentTab = Glyphs.font.currentTab
								origin = currentTab.selectedLayerOrigin
								center = NSPoint( node.position.x * scale + origin[0] , node.position.y * scale + origin[1] )
								x, y = center
								
								# Draw circle behind the node
								panel = NSRect()
								panel.size = NSSize( width + margin*2 , width + margin*2 )
								panel.origin = NSPoint( x - width/2 - margin, y - width/2 - margin )
								NSColor.colorWithCalibratedRed_green_blue_alpha_( 1,.9,.4,.7 ).set() # yellow
								NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, (width+margin*2)*0.5, (width+margin*2)*0.5 ).fill()



	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
