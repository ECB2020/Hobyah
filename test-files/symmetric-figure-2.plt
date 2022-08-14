#set terminal pdf size 29.7cm,21cm linewidth 1 font "Helvetica,22" enhanced
set terminal pngcairo size 1400,420 linewidth 3 font "Helvetica,30" enhanced
outfile = "symmetric-figure-2.png"
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
set xrange [-1650:1650]
set yrange [0:0.87]
set noxtics
set noytics

unset key
set linetype 1 linewidth 2 lc rgb "black"
set linetype 2 linewidth 1 lc rgb "green"
set linetype 3 linewidth 1 lc rgb "blue"
set linetype 4 linewidth 2 lc rgb "black" dashtype 2
set linetype 5 linewidth 1 lc rgb "black"

set arrow 1 from first 0, 0.81 to first 0, 0.7 front linetype 1 linewidth 1
set arrow 2 from first -1300, 0.32 to first -1500, 0.32 front linetype 1 linewidth 1
set arrow 3 from first  1300, 0.32 to first  1500, 0.32 front linetype 1 linewidth 1

set label 1 "{/*0.85 34 m^3/s}" at first 0, 0.85 centre
set label 2 "{/*0.85 12 m^3/s}" at first -1500, 0.26 left
set label 3 "{/*0.85 22 m^3/s}" at first 1500, 0.26 right

#set label 1 "{/*0.85 26 m^3/s}" at first 0, 0.85 centre
#set label 2 "{/*0.85 13 m^3/s}" at first -1550, 0.26 left
#set label 3 "{/*0.85 13 m^3/s}" at first 1550, 0.26 right

left1 = -800
right1 = left1 + 400
top1 = 0.3
bottom1 = 0.23

set object 51 polygon from first  left1, bottom1 to \
                           first  right1, bottom1 to \
                           first  right1, top1 to \
                           first  left1, top1 to \
                           first  left1, bottom1 fc "green" fillstyle solid

set object 52 polygon from first  -left1, bottom1 to \
                           first -right1, bottom1 to \
                           first -right1, top1 to \
                           first  -left1, top1 to \
                           first  -left1, bottom1 fc "green" fillstyle solid

jf1 = 1000
halflength = 40
support = 5
frame = 0.4
top2 = 0.38
bottom2 = 0.36
mid = 0.5 * (top2 + bottom2)
space = 50
arrowlen = 50
set object 53 polygon from first  -jf1 - halflength, bottom2 to \
                           first -jf1 + halflength, bottom2 to \
                           first -jf1 + halflength, top2 to \
                           first -jf1 + support, top2 to \
                           first -jf1 + support, frame to \
                           first -jf1 - support, frame to \
                           first -jf1 - support, top2 to \
                           first -jf1 - halflength, top2 to \
                           first -jf1 - halflength, bottom2 fc "black" fillstyle solid
set arrow 53 from first -jf1 - space, mid to -jf1 - space - arrowlen, mid  front linetype 1 linewidth 1

set object 54 polygon from first  jf1 - halflength, bottom2 to \
                           first jf1 + halflength, bottom2 to \
                           first jf1 + halflength, top2 to \
                           first jf1 + support, top2 to \
                           first jf1 + support, frame to \
                           first jf1 - support, frame to \
                           first jf1 - support, top2 to \
                           first jf1 - halflength, top2 to \
                           first jf1 - halflength, bottom2 fc "black" fillstyle solid
set arrow 54 from first jf1 + space, mid to jf1 + space + arrowlen, mid  front linetype 1 linewidth 1

plot "-" with lines linestyle 1 # Dashed black gridlines
-1500   0.2
-500    0.2
-500    0
 500    0
 500    0.2
 1500   0.2

-1500   0.4
-500    0.4
-500    0.6
 -90    0.6
 -90    0.8

  90    0.8
  90    0.6
 500    0.6
 500    0.4
 1500   0.4

e # terminates the plot data
