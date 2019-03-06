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


class showOffcurveProportions(ReporterPlugin):

	def settings(self):
		self.menuName = Glyphs.localize({'en': u'Handle Length in Percentage'})
	
	def drawRoundedRectangleForStringAtPosition(self, thisString, center, fontsize ):
		''' Adapted from Stem Thickness by Rafał Buchner '''
		scale = self.getScale()
		scaledSize = fontsize / scale
		width = len(thisString) * scaledSize
		rim = scaledSize * 0.3
		currentTab = Glyphs.font.currentTab
		origin = currentTab.selectedLayerOrigin
		center = NSPoint( center.x * scale + origin[0] , center.y * scale + origin[1] )
		x, y = center

		# Draw rounded rectangle
		panel = NSRect()
		panel.origin = NSPoint( x-width/2-rim, y-scaledSize/2-rim )
		panel.size = NSSize( width + rim*2, scaledSize + rim*2 )
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 1,.8,.2,.7 ).set()
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, scaledSize*0.5, scaledSize*0.5 ).fill()
		
		# Draw text label
		string = NSString.stringWithString_(u"%s%%" % ( thisString ) )
		textColor = NSColor.colorWithCalibratedRed_green_blue_alpha_( 0,0,0,.75 )
		attributes = NSString.drawTextAttributes_( textColor )
		textSize = string.sizeWithAttributes_(attributes)
		self.drawTextAtPoint( string, center, fontsize, align="center", fontColor=textColor )
		

	def foregroundInViewCoords(self, layer):
		scale = self.getScale()
		if layer.paths:
			for path in layer.paths:
				for node in path.nodes:
					if node.type != OFFCURVE:
						if node.nextNode.type == OFFCURVE and node.prevNode.type == OFFCURVE:
							if node.selected == True or node.nextNode.selected == True or node.prevNode.selected == True:
								hypotenuse = []
								offcurveNodes = [ node.prevNode, node.nextNode ]
								
								# Calculate the hypotenuses
								for i, offcurve in enumerate( offcurveNodes ):
									pos1 = node.position
									pos2 = offcurve.position
									hypotenuse.append( math.hypot( pos1.x - pos2.x , pos1.y - pos2.y ) )
								
								# Calculate the percentages
								factor = 100 / ( hypotenuse[0] + hypotenuse[1] )
								# Draw the percentages
								for i, offcurve in enumerate( offcurveNodes ):
									percent = int( round( hypotenuse[i] * factor, 0 ) )
									pos1 = node.position
									pos2 = offcurve.position
									labelPosition = NSPoint( pos1.x + ( pos2.x - pos1.x ) / 2 , pos1.y + ( pos2.y - pos1.y ) / 2 )
									self.drawRoundedRectangleForStringAtPosition( str(percent), labelPosition, 8 * scale )
									
								

	# def inactiveLayer(self, layer):
	# 	NSColor.redColor().set()
	# 	if layer.paths:
	# 		layer.bezierPath.fill()
	# 	if layer.components:
	# 		for component in layer.components:
	# 			component.bezierPath.fill()

	# def preview(self, layer):
	# 	NSColor.blueColor().set()
	# 	if layer.paths:
	# 		layer.bezierPath.fill()
	# 	if layer.components:
	# 		for component in layer.components:
	# 			component.bezierPath.fill()
	
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
