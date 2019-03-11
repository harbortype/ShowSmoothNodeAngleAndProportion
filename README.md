# Show Smooth Node Angle and Proportion

![](/images/preview.png)

This is a plugin for the [Glyphs font editor](https://glyphsapp.com/).  

One of the most common problems when designing multiple master and variable fonts is kinks. They happen when you have **three points in a line that have different angles between masters AND have different proportions between points**. If all of the above is true, you will get kinks in interpolations. [(Read this tutorial for more info.)](https://glyphsapp.com/tutorials/multiple-masters-part-2-keeping-your-outlines-compatible)

This reporter plugin will highlight the nodes that may produce kinks in yellow. When you select it, it will tell you the angle between the handles and their proportions. If any one of the values match the other masters (becoming light gray), a kink will not happen.

The labels will have different colors depending on what’s happening on the other masters:

![](/images/colors.png)

You also have the option to display the proportion between handles as a single ratio value. This option is accessible via context menu (Ctrl- or right-click):

![](/images/showRatio.png)

I baked a small tolerance of 1° for the angles and 1% for the proportions into the code, as it is very difficult to exactly match angles and handle lengths on a grid. If you believe these values do not produce a satisfactory result, please let me know.

### Installation

1. Download the complete ZIP file and unpack it, or clone the repository.
2. Double click the .glyphsReporter file. Confirm the dialog that appears in Glyphs.
3. Restart Glyphs

### Planned features

- Add drawing aids to make the adjustment process easier (maybe showing the other master’s corresponding nodes in the background).
