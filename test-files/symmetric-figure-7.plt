#set terminal pdf size 29.7cm,21cm linewidth 1 font "Helvetica,22" enhanced
#outfile = "symmetric-figure-4.pdf"
set terminal pngcairo size 1400,420 linewidth 3 font "Helvetica,30" enhanced
outfile = "symmetric-figure-7.png"
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


# Define a fire burning but blown to one side.  We have four tongues of flame
# with a large yellow icon overlaid with a smaller red icon.
xbase = 0
ybase = 0
width = 0.5
height = 0.0006
x101  = xbase
y101  = ybase
x102  = xbase - width  * 70
y102  = ybase + height * 30
x103  = xbase - width  * 110
y103  = ybase + height * 60
x104  = xbase - width  * 140
y104  = ybase + height * 100
x105  = xbase - width  * 150
y105  = ybase + height * 130
x106  = xbase - width  * 220
y106  = ybase + height * 160
x107  = xbase - width  * 120
y107  = ybase + height * 150
x108  = xbase - width  * 80
y108  = ybase + height * 110
x109  = xbase - width  * 80
y109  = ybase + height * 150
x110 = xbase - width  * 130
y110 = ybase + height * 165
x111 = xbase - width  * 55
y111 = ybase + height * 160
x112 = xbase - width  * 30
y112 = ybase + height * 130
x113 = xbase - width  * 15
y113 = ybase + height * 100
x114 = xbase - width  * 5
y114 = ybase + height * 140
x115 = xbase - width  * 45
y115 = ybase + height * 155
x116 = xbase + width  * 10
y116 = ybase + height * 150
x117 = xbase + width  * 5
y117 = ybase + height * 155
x118 = xbase + width  * 30
y118 = ybase + height * 155
x119 = xbase + width  * 75
y119 = ybase + height * 150
x120 = xbase + width  * 85
y120 = ybase + height * 140
x121 = xbase + width  * 85
y121 = ybase + height * 120
x122 = xbase + width  * 70
y122 = ybase + height * 70
x123 = xbase + width  * 50
y123 = ybase + height * 20
x124 = xbase
y124 = xbase


x151 = xbase - width  * 10
y151 = ybase
x152 = xbase - width  * 40
y152 = ybase + height * 15
x153 = xbase - width  * 90
y153 = ybase + height * 70
x154 = xbase - width  * 110
y154 = ybase + height * 100
x155 = xbase - width  * 120
y155 = ybase + height * 120
x156 = xbase - width  * 145
y156 = ybase + height * 140 # bend
x157 = xbase - width  * 185
y157 = ybase + height * 150 # tip
x158 = xbase - width  * 135
y158 = ybase + height * 145 # bend
x159 = xbase - width  * 85
y159 = ybase + height * 100
x160 = xbase - width  * 60
y160 = ybase + height * 70
x161 = xbase - width  * 65
y161 = ybase + height * 110
x162 = xbase - width  * 70
y162 = ybase + height * 150 # bend
x163 = xbase - width  * 100
y163 = ybase + height * 160 # tip
x164 = xbase - width  * 60
y164 = ybase + height * 155 # bend
x165 = xbase - width  * 20
y165 = ybase + height * 70
x166 = xbase + width  * 5
y166 = ybase + height * 110
x167 = xbase + width  * 10
y167 = ybase + height * 140 # bend
x168 = xbase - width  * 20
y168 = ybase + height * 150 # tip
x169 = xbase + width  * 20
y169 = ybase + height * 145 # bend
x170 = xbase + width  * 25
y170 = ybase + height * 135
x171 = xbase + width  * 20
y171 = ybase + height * 110
x172 = xbase + width  * 20
y172 = ybase + height * 70
x173 = xbase + width  * 30
y173 = ybase + height * 80
x174 = xbase + width  * 60
y174 = ybase + height * 100
x175 = xbase + width  * 70
y175 = ybase + height * 130 # bend
x176 = xbase + width  * 20
y176 = ybase + height * 150 # tip
x177 = xbase + width  * 75
y177 = ybase + height * 140 # bend
x178 = xbase + width  * 80
y178 = ybase + height * 130
x179 = xbase + width  * 70
y179 = ybase + height * 100
x180 = xbase + width  * 40
y180 = ybase + height * 20
x181 = xbase + width  * 10
y181 = ybase
x182 = xbase - width  * 10
y182 = ybase

xaxis = 1300
yaxis = 0.21
direction = +1
set object 125 polygon from first xaxis + direction * x101, yaxis + y101 to \
                            first xaxis + direction * x102, yaxis + y102 to \
                            first xaxis + direction * x103, yaxis + y103 to \
                            first xaxis + direction * x104, yaxis + y104 to \
                            first xaxis + direction * x105, yaxis + y105 to \
                            first xaxis + direction * x106, yaxis + y106 to \
                            first xaxis + direction * x107, yaxis + y107 to \
                            first xaxis + direction * x108, yaxis + y108 to \
                            first xaxis + direction * x109, yaxis + y109 to \
                            first xaxis + direction * x110, yaxis + y110 to \
                            first xaxis + direction * x111, yaxis + y111 to \
                            first xaxis + direction * x112, yaxis + y112 to \
                            first xaxis + direction * x113, yaxis + y113 to \
                            first xaxis + direction * x114, yaxis + y114 to \
                            first xaxis + direction * x115, yaxis + y115 to \
                            first xaxis + direction * x116, yaxis + y116 to \
                            first xaxis + direction * x117, yaxis + y117 to \
                            first xaxis + direction * x118, yaxis + y118 to \
                            first xaxis + direction * x119, yaxis + y119 to \
                            first xaxis + direction * x120, yaxis + y120 to \
                            first xaxis + direction * x121, yaxis + y121 to \
                            first xaxis + direction * x122, yaxis + y122 to \
                            first xaxis + direction * x123, yaxis + y123 to \
                            first xaxis + direction * x124, yaxis + y124 \
                            lw 0 fc "yellow" fillstyle solid
#                            first xaxis + direction * x127, yaxis + y127 to \
#                            first xaxis + direction * x128, yaxis + y128 to \
#                            first xaxis + direction * x129, yaxis + y129 to \
#                            first xaxis + direction * x130, yaxis + y130 to \
#                            first xaxis + direction * x131, yaxis + y131 to \
#                            first xaxis + direction * x132, yaxis + y132 \
#                            lw 0 fc "red" fillstyle solid


set object 126 polygon from first xaxis + direction * x151, yaxis + y151 to \
                            first xaxis + direction * x152, yaxis + y152 to \
                            first xaxis + direction * x153, yaxis + y153 to \
                            first xaxis + direction * x154, yaxis + y154 to \
                            first xaxis + direction * x155, yaxis + y155 to \
                            first xaxis + direction * x156, yaxis + y156 to \
                            first xaxis + direction * x157, yaxis + y157 to \
                            first xaxis + direction * x158, yaxis + y158 to \
                            first xaxis + direction * x159, yaxis + y159 to \
                            first xaxis + direction * x160, yaxis + y160 to \
                            first xaxis + direction * x161, yaxis + y161 to \
                            first xaxis + direction * x162, yaxis + y162 to \
                            first xaxis + direction * x163, yaxis + y163 to \
                            first xaxis + direction * x164, yaxis + y164 to \
                            first xaxis + direction * x165, yaxis + y165 to \
                            first xaxis + direction * x166, yaxis + y166 to \
                            first xaxis + direction * x167, yaxis + y167 to \
                            first xaxis + direction * x168, yaxis + y168 to \
                            first xaxis + direction * x169, yaxis + y169 to \
                            first xaxis + direction * x170, yaxis + y170 to \
                            first xaxis + direction * x171, yaxis + y171 to \
                            first xaxis + direction * x172, yaxis + y172 to \
                            first xaxis + direction * x173, yaxis + y173 to \
                            first xaxis + direction * x174, yaxis + y174 to \
                            first xaxis + direction * x175, yaxis + y175 to \
                            first xaxis + direction * x176, yaxis + y176 to \
                            first xaxis + direction * x177, yaxis + y177 to \
                            first xaxis + direction * x178, yaxis + y178 to \
                            first xaxis + direction * x179, yaxis + y179 to \
                            first xaxis + direction * x180, yaxis + y180 to \
                            first xaxis + direction * x181, yaxis + y181 to \
                            first xaxis + direction * x182, yaxis + y182 \
                            lw 0 fc "red" fillstyle solid

xaxis = -1300
yaxis = 0.21
direction = -1
set object 127 polygon from first xaxis + direction * x101, yaxis + y101 to \
                            first xaxis + direction * x102, yaxis + y102 to \
                            first xaxis + direction * x103, yaxis + y103 to \
                            first xaxis + direction * x104, yaxis + y104 to \
                            first xaxis + direction * x105, yaxis + y105 to \
                            first xaxis + direction * x106, yaxis + y106 to \
                            first xaxis + direction * x107, yaxis + y107 to \
                            first xaxis + direction * x108, yaxis + y108 to \
                            first xaxis + direction * x109, yaxis + y109 to \
                            first xaxis + direction * x110, yaxis + y110 to \
                            first xaxis + direction * x111, yaxis + y111 to \
                            first xaxis + direction * x112, yaxis + y112 to \
                            first xaxis + direction * x113, yaxis + y113 to \
                            first xaxis + direction * x114, yaxis + y114 to \
                            first xaxis + direction * x115, yaxis + y115 to \
                            first xaxis + direction * x116, yaxis + y116 to \
                            first xaxis + direction * x117, yaxis + y117 to \
                            first xaxis + direction * x118, yaxis + y118 to \
                            first xaxis + direction * x119, yaxis + y119 to \
                            first xaxis + direction * x120, yaxis + y120 to \
                            first xaxis + direction * x121, yaxis + y121 to \
                            first xaxis + direction * x122, yaxis + y122 to \
                            first xaxis + direction * x123, yaxis + y123 to \
                            first xaxis + direction * x124, yaxis + y124 \
                            lw 0 fc "yellow" fillstyle solid
#                            first xaxis + direction * x127, yaxis + y127 to \
#                            first xaxis + direction * x128, yaxis + y128 to \
#                            first xaxis + direction * x129, yaxis + y129 to \
#                            first xaxis + direction * x130, yaxis + y130 to \
#                            first xaxis + direction * x131, yaxis + y131 to \
#                            first xaxis + direction * x132, yaxis + y132 \
#                            lw 0 fc "red" fillstyle solid


set object 128 polygon from first xaxis + direction * x151, yaxis + y151 to \
                            first xaxis + direction * x152, yaxis + y152 to \
                            first xaxis + direction * x153, yaxis + y153 to \
                            first xaxis + direction * x154, yaxis + y154 to \
                            first xaxis + direction * x155, yaxis + y155 to \
                            first xaxis + direction * x156, yaxis + y156 to \
                            first xaxis + direction * x157, yaxis + y157 to \
                            first xaxis + direction * x158, yaxis + y158 to \
                            first xaxis + direction * x159, yaxis + y159 to \
                            first xaxis + direction * x160, yaxis + y160 to \
                            first xaxis + direction * x161, yaxis + y161 to \
                            first xaxis + direction * x162, yaxis + y162 to \
                            first xaxis + direction * x163, yaxis + y163 to \
                            first xaxis + direction * x164, yaxis + y164 to \
                            first xaxis + direction * x165, yaxis + y165 to \
                            first xaxis + direction * x166, yaxis + y166 to \
                            first xaxis + direction * x167, yaxis + y167 to \
                            first xaxis + direction * x168, yaxis + y168 to \
                            first xaxis + direction * x169, yaxis + y169 to \
                            first xaxis + direction * x170, yaxis + y170 to \
                            first xaxis + direction * x171, yaxis + y171 to \
                            first xaxis + direction * x172, yaxis + y172 to \
                            first xaxis + direction * x173, yaxis + y173 to \
                            first xaxis + direction * x174, yaxis + y174 to \
                            first xaxis + direction * x175, yaxis + y175 to \
                            first xaxis + direction * x176, yaxis + y176 to \
                            first xaxis + direction * x177, yaxis + y177 to \
                            first xaxis + direction * x178, yaxis + y178 to \
                            first xaxis + direction * x179, yaxis + y179 to \
                            first xaxis + direction * x180, yaxis + y180 to \
                            first xaxis + direction * x181, yaxis + y181 to \
                            first xaxis + direction * x182, yaxis + y182 \
                            lw 0 fc "red" fillstyle solid

set arrow 1 from first 0, 0.81 to first 0, 0.7 front linetype 1 linewidth 1
set arrow 2 from first -1900, 0.32 to first -1700, 0.32 front linetype 1 linewidth 1
set arrow 3 from first  1900, 0.32 to first  1700, 0.32 front linetype 1 linewidth 1
set arrow 4 from first -400, 0.32 to first -600, 0.32 front linetype 1 linewidth 1
set arrow 5 from first  400, 0.32 to first  600, 0.32 front linetype 1 linewidth 1
#set arrow 6 from first -1000, 0.7 to first -1000, 0.81 front linetype 1 linewidth 1
#set arrow 7 from first 1000, 0.7 to first 1000, 0.81 front linetype 1 linewidth 1

set label 1 "{/*0.85 46 m^3/s}" at first 0, 0.85 centre
set label 2 "{/*0.85 142 m^3/s}" at first -1900, 0.26 left
set label 3 "{/*0.85 142 m^3/s}" at first 1900, 0.26 right
set label 4 "{/*0.85 23 m^3/s}" at first -600, 0.26 left
set label 5 "{/*0.85 23 m^3/s}" at first  600, 0.26 right
set label 6 "{/*0.85 165 m^3/s}" at first -1000, 0.85 centre
set label 7 "{/*0.85 165 m^3/s}" at first 1000, 0.85 centre


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
