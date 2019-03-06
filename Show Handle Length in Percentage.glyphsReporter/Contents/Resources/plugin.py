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


class showHandleLengthPercentages(ReporterPlugin):

	def settings(self):
		self.menuName = Glyphs.localize({'en': u'Handle Length Percentages'})


	def getAngle(self, p1, p2):
		""" Calculates the angle between two points """
		dx, dy = p1.x - p2.x, p1.y - p2.y
		angle = math.degrees( math.atan2( dy, dx ) )
		angle = round( angle % 90, 1 )
		return angle
		

	def drawRoundedRectangleForStringAtPosition(self, length, angle, center, fontsize ):
		""" Adapted from Stem Thickness by Rafał Buchner """
		scale = self.getScale()
		scaledSize = fontsize / scale
		width = len(length) * scaledSize
		margin = 2
		currentTab = Glyphs.font.currentTab
		origin = currentTab.selectedLayerOrigin
		center = NSPoint( center.x * scale + origin[0] , center.y * scale + origin[1] )
		x, y = center

		# Configure text label
		string = NSString.stringWithString_(u"%s°\n%s%%" % ( angle, length ) )
		textColor = NSColor.colorWithCalibratedRed_green_blue_alpha_( 0,0,0,.75 )
		attributes = NSString.drawTextAttributes_( textColor )
		textSize = string.sizeWithAttributes_(attributes)
		
		# Draw rounded rectangle
		panel = NSRect()
		panel.origin = NSPoint( x-math.floor(textSize.width)/2-margin*1.5, y-textSize.height/2-margin )
		panel.size = NSSize( math.floor(textSize.width) + margin*2*1.5, textSize.height + margin*2 )
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 1,.8,.2,.7 ).set() # yellow
		NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, scaledSize*0.5, scaledSize*0.5 ).fill()
		
		# Draw text label
		self.drawTextAtPoint( string, center, fontsize, align="center", fontColor=textColor )
		

	def foregroundInViewCoords(self, layer):
		""" Draw stuff on the screen """
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
									percent = round( hypotenuse[i] * factor, 1 )
									pos1 = node.position
									pos2 = offcurve.position
									angle = self.getAngle( pos1, pos2 )
									labelPosition = NSPoint( pos1.x + ( pos2.x - pos1.x ) / 2 , pos1.y + ( pos2.y - pos1.y ) / 2 )
									self.drawRoundedRectangleForStringAtPosition( str(percent), angle, labelPosition, 8 * scale )


	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
