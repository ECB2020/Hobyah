#set terminal pdf size 29.7cm,21cm linewidth 1 font "Helvetica,22" enhanced
#outfile = "symmetric-figure-6.pdf"
set terminal pngcairo size 1400,420 linewidth 3 font "Helvetica,30" enhanced
outfile = "symmetric-figure-6.png"
set output outfile
set multiplot
unset grid
unset key

# Top left graph
set bmargin at screen 0.01
set tmargin at screen 0.99
set lmargin at screen 0.01
set rmargin at screen 0.99
unset border
unset title
unset xlabel
unset ylabel
set xrange [-2050:2050]
set yrange [0:0.88]
set noxtics
set noytics

unset key
set linetype 1 linewidth 2 lc rgb "black"
set linetype 2 linewidth 1 lc rgb "green"
set linetype 3 linewidth 1 lc rgb "blue"
set linetype 4 linewidth 2 lc rgb "black" dashtype 2
set linetype 5 linewidth 1 lc rgb "black"

left1 = -950
right1 = left1 + 400
top1 = 0.3
bottom1 = 0.23


# Define a fire burning straight up.  We have four tongues of flame
# with a large yellow icon overlaid with a smaller red icon.
xbase = 0
ybase = 0
width = 0.5
height = 0.0006
x1  = xbase
y1  = ybase
x2  = xbase - width  * 70
y2  = ybase + height * 30
x3  = xbase - width  * 110
y3  = ybase + height * 60
x4  = xbase - width  * 140
y4  = ybase + height * 100
x5  = xbase - width  * 150
y5  = ybase + height * 130
x6  = xbase - width  * 160
y6  = ybase + height * 200
x7  = xbase - width  * 130
y7  = ybase + height * 160
x8  = xbase - width  * 100
y8  = ybase + height * 110
x9  = xbase - width  * 80
y9  = ybase + height * 200
x10 = xbase - width  * 85
y10 = ybase + height * 260
x11 = xbase - width  * 75
y11 = ybase + height * 240
x12 = xbase - width  * 30
y12 = ybase + height * 130
x13 = xbase - width  * 15
y13 = ybase + height * 100
x14 = xbase - width  * 0
y14 = ybase + height * 130
x15 = xbase + width  * 40
y15 = ybase + height * 200
x16 = xbase + width  * 60
y16 = ybase + height * 255
x17 = xbase + width  * 70
y17 = ybase + height * 210
x18 = xbase + width  * 60
y18 = ybase + height * 160
x19 = xbase + width  * 40
y19 = ybase + height * 100
x20 = xbase + width  * 80
y20 = ybase + height * 130
x21 = xbase + width  * 120
y21 = ybase + height * 180
x22 = xbase + width  * 135
y22 = ybase + height * 220
x23 = xbase + width  * 145
y23 = ybase + height * 180
x24 = xbase + width  * 130
y24 = ybase + height * 120
x25 = xbase + width  * 100
y25 = ybase + height * 70
x26 = xbase + width  * 70
y26 = ybase + height * 30
x27 = xbase
y27 = xbase

x51 = xbase - width  * 10
y51 = ybase
x52 = xbase - width  * 40
y52 = ybase + height * 15
x53 = xbase - width  * 90
y53 = ybase + height * 70
x54 = xbase - width  * 120
y54 = ybase + height * 100
x55 = xbase - width  * 130
y55 = ybase + height * 120
x56 = xbase - width  * 145
y56 = ybase + height * 160
x57 = xbase - width  * 105
y57 = ybase + height * 100
x58 = xbase - width  * 60
y58 = ybase + height * 70
x59 = xbase - width  * 65
y59 = ybase + height * 110
x60 = xbase - width  * 70
y60 = ybase + height * 170
x61 = xbase - width  * 20
y61 = ybase + height * 70
x62 = xbase + width  * 10
y62 = ybase + height * 110
x63 = xbase + width  * 50
y63 = ybase + height * 190
x64 = xbase + width  * 20
y64 = ybase + height * 110
x65 = xbase + width  * 5
y65 = ybase + height * 60
x66 = xbase + width  * 50
y66 = ybase + height * 80
x67 = xbase + width  * 80
y67 = ybase + height * 100
x68 = xbase + width  * 115
y68 = ybase + height * 150
x69 = xbase + width  * 90
y69 = ybase + height * 100
x70 = xbase + width  * 40
y70 = ybase + height * 20
x71 = xbase + width  * 10
y71 = ybase
x72 = xbase - width  * 10
y72 = ybase




xaxis = -1300
yaxis = 0.21
direction = 1
set object 121 polygon from first xaxis + direction * x1, yaxis + y1 to \
                            first xaxis + direction * x2, yaxis + y2 to \
                            first xaxis + direction * x3, yaxis + y3 to \
                            first xaxis + direction * x4, yaxis + y4 to \
                            first xaxis + direction * x5, yaxis + y5 to \
                            first xaxis + direction * x6, yaxis + y6 to \
                            first xaxis + direction * x7, yaxis + y7 to \
                            first xaxis + direction * x8, yaxis + y8 to \
                            first xaxis + direction * x9, yaxis + y9 to \
                            first xaxis + direction * x10, yaxis + y10 to \
                            first xaxis + direction * x11, yaxis + y11 to \
                            first xaxis + direction * x12, yaxis + y12 to \
                            first xaxis + direction * x13, yaxis + y13 to \
                            first xaxis + direction * x14, yaxis + y14 to \
                            first xaxis + direction * x15, yaxis + y15 to \
                            first xaxis + direction * x16, yaxis + y16 to \
                            first xaxis + direction * x17, yaxis + y17 to \
                            first xaxis + direction * x18, yaxis + y18 to \
                            first xaxis + direction * x19, yaxis + y19 to \
                            first xaxis + direction * x20, yaxis + y20 to \
                            first xaxis + direction * x21, yaxis + y21 to \
                            first xaxis + direction * x22, yaxis + y22 to \
                            first xaxis + direction * x23, yaxis + y23 to \
                            first xaxis + direction * x24, yaxis + y24 to \
                            first xaxis + direction * x25, yaxis + y25 to \
                            first xaxis + direction * x26, yaxis + y26 to \
                            first xaxis + direction * x27, yaxis + y27\
                            lw 0 fc "yellow" fillstyle solid
set object 122 polygon from first xaxis + direction * x51, yaxis + y51 to \
                            first xaxis + direction * x52, yaxis + y52 to \
                            first xaxis + direction * x53, yaxis + y53 to \
                            first xaxis + direction * x54, yaxis + y54 to \
                            first xaxis + direction * x55, yaxis + y55 to \
                            first xaxis + direction * x56, yaxis + y56 to \
                            first xaxis + direction * x57, yaxis + y57 to \
                            first xaxis + direction * x58, yaxis + y58 to \
                            first xaxis + direction * x59, yaxis + y59 to \
                            first xaxis + direction * x60, yaxis + y60 to \
                            first xaxis + direction * x61, yaxis + y61 to \
                            first xaxis + direction * x62, yaxis + y62 to \
                            first xaxis + direction * x63, yaxis + y63 to \
                            first xaxis + direction * x64, yaxis + y64 to \
                            first xaxis + direction * x65, yaxis + y65 to \
                            first xaxis + direction * x66, yaxis + y66 to \
                            first xaxis + direction * x67, yaxis + y67 to \
                            first xaxis + direction * x68, yaxis + y68 to \
                            first xaxis + direction * x69, yaxis + y69 to \
                            first xaxis + direction * x70, yaxis + y70 to \
                            first xaxis + direction * x71, yaxis + y71 to \
                            first xaxis + direction * x72, yaxis + y72 \
                            lw 0 fc "red" fillstyle solid

xaxis = 1300
yaxis = 0.21
direction = -1
set object 123 polygon from first xaxis + direction * x1, yaxis + y1 to \
                            first xaxis + direction * x2, yaxis + y2 to \
                            first xaxis + direction * x3, yaxis + y3 to \
                            first xaxis + direction * x4, yaxis + y4 to \
                            first xaxis + direction * x5, yaxis + y5 to \
                            first xaxis + direction * x6, yaxis + y6 to \
                            first xaxis + direction * x7, yaxis + y7 to \
                            first xaxis + direction * x8, yaxis + y8 to \
                            first xaxis + direction * x9, yaxis + y9 to \
                            first xaxis + direction * x10, yaxis + y10 to \
                            first xaxis + direction * x11, yaxis + y11 to \
                            first xaxis + direction * x12, yaxis + y12 to \
                            first xaxis + direction * x13, yaxis + y13 to \
                            first xaxis + direction * x14, yaxis + y14 to \
                            first xaxis + direction * x15, yaxis + y15 to \
                            first xaxis + direction * x16, yaxis + y16 to \
                            first xaxis + direction * x17, yaxis + y17 to \
                            first xaxis + direction * x18, yaxis + y18 to \
                            first xaxis + direction * x19, yaxis + y19 to \
                            first xaxis + direction * x20, yaxis + y20 to \
                            first xaxis + direction * x21, yaxis + y21 to \
                            first xaxis + direction * x22, yaxis + y22 to \
                            first xaxis + direction * x23, yaxis + y23 to \
                            first xaxis + direction * x24, yaxis + y24 to \
                            first xaxis + direction * x25, yaxis + y25 to \
                            first xaxis + direction * x26, yaxis + y26 to \
                            first xaxis + direction * x27, yaxis + y27\
                            lw 0 fc "yellow" fillstyle solid
set object 124 polygon from first xaxis + direction * x51, yaxis + y51 to \
                            first xaxis + direction * x52, yaxis + y52 to \
                            first xaxis + direction * x53, yaxis + y53 to \
                            first xaxis + direction * x54, yaxis + y54 to \
                            first xaxis + direction * x55, yaxis + y55 to \
                            first xaxis + direction * x56, yaxis + y56 to \
                            first xaxis + direction * x57, yaxis + y57 to \
                            first xaxis + direction * x58, yaxis + y58 to \
                            first xaxis + direction * x59, yaxis + y59 to \
                            first xaxis + direction * x60, yaxis + y60 to \
                            first xaxis + direction * x61, yaxis + y61 to \
                            first xaxis + direction * x62, yaxis + y62 to \
                            first xaxis + direction * x63, yaxis + y63 to \
                            first xaxis + direction * x64, yaxis + y64 to \
                            first xaxis + direction * x65, yaxis + y65 to \
                            first xaxis + direction * x66, yaxis + y66 to \
                            first xaxis + direction * x67, yaxis + y67 to \
                            first xaxis + direction * x68, yaxis + y68 to \
                            first xaxis + direction * x69, yaxis + y69 to \
                            first xaxis + direction * x70, yaxis + y70 to \
                            first xaxis + direction * x71, yaxis + y71 to \
                            first xaxis + direction * x72, yaxis + y72 \
                            lw 0 fc "red" fillstyle solid


# Define the impeller of an axial fan
diameter = 180
bladechord = 0.015
arrowlen = 6 * bladechord
bladelength = 0.5 * diameter * 0.75
hub = 0.5 * diameter - bladelength
x1 = 0
y1 = bladechord * 0.8
x2 = hub * 0.9
y2 = bladechord * 0.8
x3 = hub
y3 = bladechord * 0.75

x4 = hub
y4 = bladechord * 0.3
x5 = hub + bladelength * 0.1
y5 = bladechord * 0.3
x6 = hub + bladelength * 0.15
y6 = bladechord
x7 = hub + bladelength * 0.98
y7 = bladechord * 0.7
x8 = hub + bladelength * 1
y8 = 0
x17 = hub + bladelength * 0.98
y17 = -bladechord * 0.7
x16 = hub + bladelength * 0.15
y16 = -bladechord
x15 = hub + bladelength * 0.1
y15 = -bladechord * 0.3
x14 = hub
y14 = -bladechord * 0.3
x13 = hub
y13 = -bladechord * 0.75
x12 = hub * 0.9
y12 = -bladechord * 0.8
x11 = 0
y11 = -bladechord * 0.8



# Set the fan icon in the left-hand shaft
xaxis = -1000
yaxis = 0.45
set object 153 polygon from first xaxis + x1, yaxis + y1 to \
                            first xaxis + x2, yaxis + y2 to \
                            first xaxis + x3, yaxis + y3 to \
                            first xaxis + x4, yaxis + y4 to \
                            first xaxis + x5, yaxis + y5 to \
                            first xaxis + x6, yaxis + y6 to \
                            first xaxis + x7, yaxis + y7 to \
                            first xaxis + x8, yaxis + y8 to \
                            first xaxis + x17, yaxis + y17 to \
                            first xaxis + x16, yaxis + y16 to \
                            first xaxis + x15, yaxis + y15 to \
                            first xaxis + x14, yaxis + y14 to \
                            first xaxis + x13, yaxis + y13 to \
                            first xaxis + x12, yaxis + y12 to \
                            first xaxis + x11, yaxis + y11 to\
                            first xaxis - x11, yaxis + y11 to \
                            first xaxis - x12, yaxis + y12 to \
                            first xaxis - x13, yaxis + y13 to \
                            first xaxis - x14, yaxis + y14 to \
                            first xaxis - x15, yaxis + y15 to \
                            first xaxis - x16, yaxis + y16 to \
                            first xaxis - x17, yaxis + y17 to \
                            first xaxis - x8, yaxis + y8 to \
                            first xaxis - x7, yaxis + y7 to \
                            first xaxis - x6, yaxis + y6 to \
                            first xaxis - x5, yaxis + y5 to \
                            first xaxis - x4, yaxis + y4 to \
                            first xaxis - x3, yaxis + y3 to \
                            first xaxis - x2, yaxis + y2 to \
                            first xaxis - x1, yaxis + y1 \
                            lw 0 fc "gray" fillstyle solid
set arrow 154 from first xaxis, yaxis - arrowlen * 0.4 \
              to   first xaxis, yaxis + arrowlen * 0.6 \
              front linetype 1 linewidth 1

# Set the fan icon in the right-hand shaft
xaxis = 1000
yaxis = 0.75
set object 155 polygon from first xaxis + x1, yaxis + y1 to \
                            first xaxis + x2, yaxis + y2 to \
                            first xaxis + x3, yaxis + y3 to \
                            first xaxis + x4, yaxis + y4 to \
                            first xaxis + x5, yaxis + y5 to \
                            first xaxis + x6, yaxis + y6 to \
                            first xaxis + x7, yaxis + y7 to \
                            first xaxis + x8, yaxis + y8 to \
                            first xaxis + x17, yaxis + y17 to \
                            first xaxis + x16, yaxis + y16 to \
                            first xaxis + x15, yaxis + y15 to \
                            first xaxis + x14, yaxis + y14 to \
                            first xaxis + x13, yaxis + y13 to \
                            first xaxis + x12, yaxis + y12 to \
                            first xaxis + x11, yaxis + y11 to\
                            first xaxis - x11, yaxis + y11 to \
                            first xaxis - x12, yaxis + y12 to \
                            first xaxis - x13, yaxis + y13 to \
                            first xaxis - x14, yaxis + y14 to \
                            first xaxis - x15, yaxis + y15 to \
                            first xaxis - x16, yaxis + y16 to \
                            first xaxis - x17, yaxis + y17 to \
                            first xaxis - x8, yaxis + y8 to \
                            first xaxis - x7, yaxis + y7 to \
                            first xaxis - x6, yaxis + y6 to \
                            first xaxis - x5, yaxis + y5 to \
                            first xaxis - x4, yaxis + y4 to \
                            first xaxis - x3, yaxis + y3 to \
                            first xaxis - x2, yaxis + y2 to \
                            first xaxis - x1, yaxis + y1 \
                            lw 0 fc "gray" fillstyle solid
set arrow 156 from first xaxis, yaxis - arrowlen * 0.4 \
              to   first xaxis, yaxis + arrowlen * 0.6 \
              front linetype 1 linewidth 1

set label 1 "{/*0.5 Back end}" at first -850, 0.45 left
set label 2 "{/*0.5 Forward end}" at first -850, 0.79 left
set label 3 "{/*0.5 Back end}" at first 1150, 0.79 left
set label 4 "{/*0.5 Forward end}" at first 1150, 0.45 left
set label 5 "{/*0.5 Extract fan}" at first -1125, 0.47 right
set label 6 "{/*0.5 Extract fan}" at first 875, 0.77 right


plot "-" with lines linestyle 1 # Dashed black gridlines
-2000   0.2
 2000    0.2

-2000   0.4
-1100    0.4
-1100    0.8

-900     0.8
-900     0.4
-100     0.4
-100     0.8

 100     0.8
 100     0.4
 900     0.4
 900     0.8

 2000   0.4
 1100    0.4
 1100    0.8
e # terminates the plot data
