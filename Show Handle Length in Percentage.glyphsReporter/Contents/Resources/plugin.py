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

handleSize = 5 + Glyphs.handleSize * 2.5 # (= 5.0 or 7.5 or 10.0)

class showHandleLengthPercentages(ReporterPlugin):

	def settings(self):
		self.menuName = Glyphs.localize({'en': u'Handle Length Percentages'})


	def getAngle(self, p1, p2):
		""" Calculates the angle between two points """
		dx, dy = p1.x - p2.x, p1.y - p2.y
		angle = math.degrees( math.atan2( dy, dx ) )
		angle = round( angle % 90, 1 )
		return angle
		

	def drawRoundedRectangleForStringAtPosition(self, string, center, fontsize, isAngle=False ):
		""" Adapted from Stem Thickness by Rafał Buchner """
		scale = self.getScale()
		scaledSize = fontsize / scale
		width = len(string) * scaledSize
		margin = 2
		currentTab = Glyphs.font.currentTab
		origin = currentTab.selectedLayerOrigin
		center = NSPoint( center.x * scale + origin[0] , center.y * scale + origin[1] )
		x, y = center

		# Configure text label
		string = NSString.stringWithString_(string)
		textColor = NSColor.colorWithCalibratedRed_green_blue_alpha_( 0,0,0,.75 )
		attributes = NSString.drawTextAttributes_( textColor )
		textSize = string.sizeWithAttributes_(attributes)
		
		# Draw rounded rectangle
		panel = NSRect()
		panel.size = NSSize( math.floor(textSize.width) + margin*2*1.5, textSize.height + margin*2 )
		if isAngle == True:
			panel.origin = NSPoint( 
				x-math.floor(textSize.width)/2-margin*1.5, 
				y-textSize.height/2-margin + textSize.height/2 + handleSize+4 )
		else:
			panel.origin = NSPoint( 
				x-math.floor(textSize.width)/2-margin*1.5, 
				y-textSize.height/2-margin )
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 1,.8,.2,.7 ).set() # yellow
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, scaledSize*0.5, scaledSize*0.5 ).fill()
		
		# Draw text label
		if isAngle == True:
			center = NSPoint( x, y + textSize.height/2 + handleSize+4 )
		self.drawTextAtPoint( string, center, fontsize, align="center", fontColor=textColor )
		

	def foregroundInViewCoords(self, layer):
		""" Draw stuff on the screen """
		scale = self.getScale()
		if layer.paths:
			for path in layer.paths:
				for node in path.nodes:
					if node.smooth == True:
						if node.selected == True or node.nextNode.selected == True or node.prevNode.selected == True:
							hypotenuses = []
							offcurveNodes = [ node.prevNode, node.nextNode ]
							
							# Calculate the hypotenuses
							for i, offcurve in enumerate( offcurveNodes ):
								pos1 = node.position
								pos2 = offcurve.position
								hypotenuses.append( math.hypot( pos1.x - pos2.x , pos1.y - pos2.y ) )
							
							# Calculate the percentages
							factor = 100 / ( hypotenuses[0] + hypotenuses[1] )
							# Draw the percentages
							for i, offcurve in enumerate( offcurveNodes ):
								percent = round( hypotenuses[i] * factor, 1 )
								pos1 = node.position
								pos2 = offcurve.position
								labelPosition = NSPoint( pos1.x + ( pos2.x - pos1.x ) / 2 , pos1.y + ( pos2.y - pos1.y ) / 2 )
								self.drawRoundedRectangleForStringAtPosition( u"%s%%" % str(percent), labelPosition, 8 * scale )

							# Draw the angle
							pos1 = node.prevNode.position
							pos2 = node.nextNode.position
							angle = self.getAngle( pos1, pos2 )
							labelPosition = NSPoint( node.position.x , node.position.y )
							self.drawRoundedRectangleForStringAtPosition( u"%s°" % str(angle), labelPosition, 8 * scale, isAngle=True )


	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
