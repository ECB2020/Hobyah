# A gnuplot file for plotting the test data from the 1985 temperature tests
# of a diesel freight train going uphill through the Woy Woy tunnel in northern
# New South Wales.  The original data is from the NSW SRA's test report.
#
# The Woy Woy tunnel is a straight, twin-track, horseshoe shaped brick tunnel
# built in the 1880s.  It is 1.79 km long and has a 1 in 150 gradient.
#
# Three tests were run, with two locos hauling a load uphill through the
# tunnel.  The second locos was heavily instrumented (temperature sensors)
# Two runs were made at notch 8 (full power) and one at notch 6.
#
# These tests led to the bodyshells of the class 81 locos being modified.
# The engine air intakes were moved lower down on the bodyshell so that the
# engine drew in cooler air when passing through a tunnel.

set terminal pdf size 21cm, 29.7cm enhanced
set output "Woy-Woy-1985-test-plots-5.pdf"
set multiplot

# Set the X axis data format in the data files.
set xdata time
set timefmt "%H:%M:%S"

# Page title and a QA label text.
set label 1 "{/*1.5 1985 SRA diesel freight loco tests (81 class) in Woy Woy tunnel, test A (notch 8, 36-40 km/h)}" at screen 0.5, 0.92 center
set label 101 "{/*0.55 Page 1 of Woy-Woy-1985-test-plots-5.plt}" at screen 0.935, 0.02 right

# Define variables that set where the labels and arrows go.  We adjust some
# of these for the different graphs.
DMCy   = -1            # Base position for the DMC labels/arrows on the Y axis
DMCup1 = -4            # Offset from the base position, to where km post arrows start on the Y axis
DMCup2 = -8            # Offset to where km post arrows ends on the Y axis
tlabel = "00:31:52"    # Position at which the DMC label goes on the X axis
t71    = "00:32:52"    # When the DMC passes the 71 km post on the X axis
t70    = "00:33:58"
t69    = "00:35:24"
tentry = "00:35:40"    # When the DMC enters the tunnel
t68    = "00:36:58"
texit  = "00:38:25"    # When the DMC exits the tunnel
t66    = "00:40:02"
DMCup3 = 9             # Position at which the train entry/exit arrows start on the Y axis
DMCup4 = +16           # Position at which the train entry/exit arrows finish on the Y axis
BVy = 3                # Base position for the brake van labels/arrows goes on the Y axis
BVup1 = 9              # Position at which brake van entry/exit arrows start on the Y axis
BVup2 = +11.5          # Position at which brake van entry/exit arrows finish on the Y axis
BVentry = "00:36:19.2" # When the brake van enters on the X axis
BVexit = "00:39:14.4"  # When the brake van exits on the X axis

# Top graph on page 1
set title "Locomotive cooling system temperature measurements (on loco 8117)"
set xrange ["00:24:50":"00:45:15"]
set xlabel "Time"
set ylabel "Temperature (deg C)"
set bmargin at screen 0.65
set tmargin at screen 0.87
set lmargin at screen 0.12
set rmargin at screen 0.87
set xtics format "%Hh:%Mm"
set grid xtics mxtics ytics y2tics
set yrange [-10:90]
set ytics 10
set label 2 "{/*0.9 DMC (dynamometer car) times at kilometre posts:}" at first tlabel, first DMCy right
set label 3 "{/*0.9 71 km}" at first t71, first DMCy center
set arrow 3 from first t71, first DMCy+DMCup1 to t71, first DMCy+DMCup2 head
set label 4 "{/*0.9 70 km}" at first t70, first DMCy center
set arrow 4 from first t70, first DMCy+DMCup1 to t70, first DMCy+DMCup2 head
set label 5 "{/*0.9 69 km}" at first t69, first DMCy center
set arrow 5 from first t69, first DMCy+DMCup1 to t69, first DMCy+DMCup2 head
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 7 "{/*0.9 68 km}" at first t68, first DMCy center
set arrow 7 from first t68, first DMCy+DMCup1 to t68, first DMCy+DMCup2 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
set label 9 "{/*0.9 66 km}" at first t66, first DMCy center
set arrow 9 from first t66, first DMCy+DMCup1 to t66, first DMCy+DMCup2 head
set key top left reverse Left font "arial,14"
set ytics ("" -10, "0" 0, "10" 10, "20" 20, "30" 30, "40" 40, "50" 50, "60" 60, "70" 70, "80" 80, "90" 90)
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:4 title "103, water temperature into heat exchanger" with lines, \
"" using 1:3 title "102, water temperature out of heat exchanger" with lines, \
"" using 1:15 title "114, air temperature into leading end of radiator on LH side next to tunnel wall" with lines lc "black" , \
"" using 1:16 title "115, air temperature into midpoint of radiator on LH side" with lines lc "red", \
"" using 1:17 title "116, air temperature into trailing end of radiator on LH side" with lines lc "green", \
"" using 1:12 title "111, air temperature into leading end of radiator on RH side next to empty track" with lines lc "black" lw 4, \
"" using 1:13 title "112, air temperature into midpoint of radiator on RH side" with lines lc "red" lw 4, \
"" using 1:14 title "113, air temperature into trailing end of radiator on RH side" with lines lc "green" lw 4
unset label
unset arrow


# Middle graph on page 1
DMCup3 = 12
DMCup4 = +16
set title "Engine air intake temperature measurements (on loco 8117)"
set bmargin at screen 0.37
set tmargin at screen 0.59
set lmargin at screen 0.12
set rmargin at screen 0.87
set yrange [0:36]
set ytics 5
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:10 title "109, air temperature into engine on LH side next to tunnel wall" with lines lc "green", \
"" using 1:11 title "110, air temperature into engine on RH side next to empty track" with lines lc "black" lw 4, \
"" using 1:9 title "108, air temperature out of inertial filter" with lines lc "yellow" lw 2


# First bottom graph on page 1
set title "Air temperature measurements alongside DMC (directly behind loco 8117), at the brake van (separated from the DMC by 21 coal wagons) and in the tunnel"
DMCup3 = 12
DMCup4 = +16
set bmargin at screen 0.09
set tmargin at screen 0.31
set lmargin at screen 0.12
set rmargin at screen 0.87
set yrange [0:36]
set ytics 5
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:7 title "106, air temperature alongside DMC 2 m up on LH side next to tunnel wall" with lines lc "red", \
"" using 1:8 title "107, air temperature alongside DMC 4 m upon LH side" with lines lc "green", \
"" using 1:5 title "104, air temperature alongside DMC 2 m up on RH side next to empty track" with lines lc "red" lw 4, \
"" using 1:6 title "105, air temperature alongside DMC 4 m up on RH side" with lines lc "green" lw 4
set key bottom left reverse Left font "arial,14"
# Second bottom graph on page 1, without a border (so the graph key can be split in two).
unset title
unset xlabel
unset ylabel
unset ytics
unset xtics
unset border
unset grid
set label 6 "{/*0.9 BV enters}" at first BVentry, first BVy+BVup1-1 center
set arrow 6 from first BVentry, first BVy+BVup1 to BVentry, first BVy+BVup2 head
set label 8 "{/*0.9 BV exits}" at first BVexit, first BVy+BVup1-1 center
set arrow 8 from first BVexit, first BVy+BVup1 to BVexit, first BVy+BVup2 head
plot "Woy-Woy-1985-test-brake-van-TC3.txt" using 1:3 title "3, air temperature alongside brake van 2 m up on LH side" with points pt 1  pointsize 0.5 lc "blue" lw 1 axes x1y1, \
"Woy-Woy-1985-test-brake-van-TC4.txt" using 1:3 title "4, air temperature alongside brake van 4 m upon LH side" with points pt 2 ps 0.5 lc "green" axes x1y1, \
"Woy-Woy-1985-test-brake-van-TC1.txt" using 1:3 title "1, air temperature alongside brake van 2 m up on RH side" with points pt 3 ps 0.3 lc "black" lw 5 axes x1y1 , \
"Woy-Woy-1985-test-brake-van-TC2.txt" using 1:3 title "2, air temperature alongside brake van 4 m up on RH side" with points pt 4 ps 0.2 lc "red" lw 5 axes x1y1, \
"Woy-Woy-1985-test-68-km-post.txt" using 1:2 title "Ad hoc measurement: handheld temperature sensor in the tunnel near the 68 km marker plate" with points pt 5 ps 0.5 lc "yellow" lw 5 axes x1y1
#reset border


unset multiplot # start a new page
set multiplot
set label 101 "{/*0.55 Page 2 of Woy-Woy-1985-test-plots-5.plt}" at screen 0.935, 0.02 right
set label 1 "{/*1.5 1985 SRA diesel freight loco tests (81 class) in Woy Woy tunnel, test C (notch 8, 34-35 km/h)}" at screen 0.5, 0.92 center
set xrange ["04:02:46":"04:23:11"]
tlabel = "04:11:00"
t71    = "04:04:07"
t70    = "04:05:37"
t69    = "04:12:54"
tentry = "04:13:36"
t68    = "04:15:30"
texit  = "04:17:07"
t66    = "04:18:55"
DMCup3 = 9
DMCup4 = +16
BVentry = "04:14:40"
BVexit = "04:17:43"
# Top graph on page 2
set border
set title "Locomotive cooling system temperature measurements (on loco 8117)"
set xlabel "Time"
set ylabel "Temperature (deg C)"
set bmargin at screen 0.65
set tmargin at screen 0.87
set lmargin at screen 0.12
set rmargin at screen 0.87
set xtics format "%Hh:%Mm"
set grid xtics mxtics ytics y2tics
set yrange [-10:90]
set ytics 10
set label 2 "{/*0.9 DMC times at kilometre posts:}" at first tlabel, first DMCy right
set label 3 "{/*0.9 71 km}" at first t71, first DMCy center
set arrow 3 from first t71, first DMCy+DMCup1 to t71, first DMCy+DMCup2 head
set label 4 "{/*0.9 70 km}" at first t70, first DMCy center
set arrow 4 from first t70, first DMCy+DMCup1 to t70, first DMCy+DMCup2 head
set label 5 "{/*0.9 69 km}" at first t69, first DMCy center
set arrow 5 from first t69, first DMCy+DMCup1 to t69, first DMCy+DMCup2 head
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 7 "{/*0.9 68 km}" at first t68, first DMCy center
set arrow 7 from first t68, first DMCy+DMCup1 to t68, first DMCy+DMCup2 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
set label 9 "{/*0.9 66 km}" at first t66, first DMCy center
set arrow 9 from first t66, first DMCy+DMCup1 to t66, first DMCy+DMCup2 head
set key top left reverse Left font "arial,14"
set ytics ("" -10, "0" 0, "10" 10, "20" 20, "30" 30, "40" 40, "50" 50, "60" 60, "70" 70, "80" 80, "90" 90)
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:4 title "103, water temperature into heat exchanger" with lines, \
"" using 1:3 title "102, water temperature out of heat exchanger" with lines, \
"" using 1:15 title "114, air temperature into leading end of radiator on LH side" with lines lc "black" , \
"" using 1:16 title "115, air temperature into midpoint of radiator on LH side" with lines lc "red", \
"" using 1:17 title "116, air temperature into trailing end of radiator on LH side" with lines lc "green", \
"" using 1:12 title "111, air temperature into leading end of radiator on RH side next to empty track" with lines lc "black" lw 4, \
"" using 1:13 title "112, air temperature into midpoint of radiator on RH side" with lines lc "red" lw 4, \
"" using 1:14 title "113, air temperature into trailing end of radiator on RH side" with lines lc "green" lw 4
unset label
unset arrow


# Middle graph on page 2
DMCup3 = 12
DMCup4 = +16
set title "Engine air intake temperature measurements (on loco 8117)"
set bmargin at screen 0.37
set tmargin at screen 0.59
set lmargin at screen 0.12
set rmargin at screen 0.87
set yrange [0:36]
set ytics 5
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:10 title "109, air temperature into engine on LH side next to tunnel wall" with lines lc "green", \
"" using 1:11 title "110, air temperature into engine on RH side next to empty track" with lines lc "black" lw 4, \
"" using 1:9 title "108, air temperature out of inertial filter" with lines lc "yellow" lw 2


# First bottom graph on page 2
set title "Air temperature measurements alongside DMC (directly behind loco 8117), at the brake van (separated from the DMC by 21 coal wagons) and in the tunnel"
DMCup3 = 12
DMCup4 = +16
set bmargin at screen 0.09
set tmargin at screen 0.31
set lmargin at screen 0.12
set rmargin at screen 0.87
set yrange [0:36]
set ytics 5
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:7 title "106, air temperature alongside DMC 2 m up on LH side next to tunnel wall" with lines lc "red", \
"" using 1:8 title "107, air temperature alongside DMC 4 m upon LH side" with lines lc "green", \
"" using 1:5 title "104, air temperature alongside DMC 2 m up on RH side next to empty track" with lines lc "red" lw 4, \
"" using 1:6 title "105, air temperature alongside DMC 4 m up on RH side" with lines lc "green" lw 4
set key bottom left reverse Left font "arial,14"
# Second bottom graph on page 2 (no border)
unset title
unset xlabel
unset ylabel
unset ytics
unset xtics
unset border
unset grid
set label 6 "{/*0.9 BV enters}" at first BVentry, first BVy+BVup1-1 center
set arrow 6 from first BVentry, first BVy+BVup1 to BVentry, first BVy+BVup2 head
set label 8 "{/*0.9 BV exits}" at first BVexit, first BVy+BVup1-1 center
set arrow 8 from first BVexit, first BVy+BVup1 to BVexit, first BVy+BVup2 head
plot "Woy-Woy-1985-test-brake-van-TC3.txt" using 1:3 title "3, air temperature alongside brake van 2 m up on LH side" with points pt 1  pointsize 0.5 lc "blue" lw 1 axes x1y1, \
"Woy-Woy-1985-test-brake-van-TC4.txt" using 1:3 title "4, air temperature alongside brake van 4 m upon LH side" with points pt 2 ps 0.5 lc "green" axes x1y1, \
"Woy-Woy-1985-test-brake-van-TC1.txt" using 1:3 title "1, air temperature alongside brake van 2 m up on RH side" with points pt 3 ps 0.3 lc "black" lw 5 axes x1y1 , \
"Woy-Woy-1985-test-brake-van-TC2.txt" using 1:3 title "2, air temperature alongside brake van 4 m up on RH side" with points pt 4 ps 0.2 lc "red" lw 5 axes x1y1, \
"Woy-Woy-1985-test-68-km-post.txt" using 1:2 title "Ad hoc measurement: handheld temperature sensor in the tunnel near the 68 km marker plate" with points pt 5 ps 0.5 lc "yellow" lw 5 axes x1y1
#reset border


unset multiplot # start a new page
set multiplot
set label 1 "{/*1.5 1985 SRA diesel freight loco tests (81 class) in Woy Woy tunnel, test B (notch 6, approx. 25 km/h)}" at screen 0.5, 0.92 center
set label 101 "{/*0.55 Page 3 of Woy-Woy-1985-test-plots-5.plt}" at screen 0.935, 0.02 right
set lmargin at screen 0.12
set rmargin at screen 0.87
set bmargin at screen 0.12
set tmargin at screen 0.87
set xrange ["02:22:49":"02:43:14"]
tlabel = "02:28:45"
t71    = "02:29:45"
t70    = "02:31:01"
t69    = "02:33:10"
tentry = "02:33:39"
t68    = "02:35:50"
texit  = "02:38:04"
t66    = "02:39:56"
DMCup3 = 9
DMCup4 = +16
BVentry = "02:34:50.4"
BVexit = "02:39:00"


# Top graph on page 3
set border
set title "Locomotive cooling system temperature measurements (on loco 8117)"
set xlabel "Time"
set ylabel "Temperature (deg C)"
set bmargin at screen 0.65
set tmargin at screen 0.87
set lmargin at screen 0.12
set rmargin at screen 0.87
set xtics format "%Hh:%Mm"
set grid xtics mxtics ytics y2tics
set yrange [-10:90]
set ytics 10
set label 2 "{/*0.9 DMC times at kilometre posts:}" at first tlabel, first DMCy right
set label 3 "{/*0.9 71 km}" at first t71, first DMCy center
set arrow 3 from first t71, first DMCy+DMCup1 to t71, first DMCy+DMCup2 head
set label 4 "{/*0.9 70 km}" at first t70, first DMCy center
set arrow 4 from first t70, first DMCy+DMCup1 to t70, first DMCy+DMCup2 head
set label 5 "{/*0.9 69 km}" at first t69, first DMCy center
set arrow 5 from first t69, first DMCy+DMCup1 to t69, first DMCy+DMCup2 head
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 7 "{/*0.9 68 km}" at first t68, first DMCy center
set arrow 7 from first t68, first DMCy+DMCup1 to t68, first DMCy+DMCup2 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
set label 9 "{/*0.9 66 km}" at first t66, first DMCy center
set arrow 9 from first t66, first DMCy+DMCup1 to t66, first DMCy+DMCup2 head
set key top left reverse Left font "arial,14"
set ytics ("" -10, "0" 0, "10" 10, "20" 20, "30" 30, "40" 40, "50" 50, "60" 60, "70" 70, "80" 80, "90" 90)
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:4 title "103, water temperature into heat exchanger" with lines, \
"" using 1:3 title "102, water temperature out of heat exchanger" with lines, \
"" using 1:15 title "114, air temperature into leading end of radiator on LH side next to tunnel wall" with lines lc "black" , \
"" using 1:16 title "115, air temperature into midpoint of radiator on LH side" with lines lc "red", \
"" using 1:17 title "116, air temperature into trailing end of radiator on LH side" with lines lc "green", \
"" using 1:12 title "111, air temperature into leading end of radiator on RH side next to empty track" with lines lc "black" lw 4, \
"" using 1:13 title "112, air temperature into midpoint of radiator on RH side" with lines lc "red" lw 4, \
"" using 1:14 title "113, air temperature into trailing end of radiator on RH side" with lines lc "green" lw 4
unset label
unset arrow


# Middle graph on page 3
DMCup3 = 12
DMCup4 = +16
set title "Engine air intake temperature measurements (on loco 8117)"
set bmargin at screen 0.37
set tmargin at screen 0.59
set lmargin at screen 0.12
set rmargin at screen 0.87
set yrange [0:36]
set ytics 5
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:10 title "109, air temperature into engine on LH side next to tunnel wall" with lines lc "green", \
"" using 1:11 title "110, air temperature into engine on RH side next to empty track" with lines lc "black" lw 4, \
"" using 1:9 title "108, air temperature out of inertial filter" with lines lc "yellow" lw 2


# First bottom graph on page 3
set title "Air temperature measurements alongside DMC (directly behind loco 8117), at the brake van (separated from the DMC by 21 coal wagons) and in the tunnel"
DMCup3 = 12
DMCup4 = +16
set bmargin at screen 0.09
set tmargin at screen 0.31
set lmargin at screen 0.12
set rmargin at screen 0.87
set yrange [0:36]
set ytics 5
set label 6 "{/*0.9 DMC enters}" at first tentry, first DMCy+DMCup3-1 center
set arrow 6 from first tentry, first DMCy+DMCup3 to tentry, first DMCy+DMCup4 head
set label 8 "{/*0.9 DMC exits}" at first texit, first DMCy+DMCup3-1 center
set arrow 8 from first texit, first DMCy+DMCup3 to texit, first DMCy+DMCup4 head
plot "Woy-Woy-1985-test-data-Digistrip.txt" \
using 1:2 title "101, air temperature ahead of train" with lines lc "purple" lw 2, \
"" using 1:7 title "106, air temperature alongside DMC 2 m up on LH side next to tunnel wall" with lines lc "red", \
"" using 1:8 title "107, air temperature alongside DMC 4 m upon LH side" with lines lc "green", \
"" using 1:5 title "104, air temperature alongside DMC 2 m up on RH side next to empty track" with lines lc "red" lw 4, \
"" using 1:6 title "105, air temperature alongside DMC 4 m up on RH side" with lines lc "green" lw 4
# Second bottom graph on page 3 (no border)
set key bottom left reverse Left font "arial,14"
unset title
unset xlabel
unset ylabel
unset ytics
unset xtics
unset border
unset grid
set label 6 "{/*0.9 BV enters}" at first BVentry, first BVy+BVup1-1 center
set arrow 6 from first BVentry, first BVy+BVup1 to BVentry, first BVy+BVup2 head
set label 8 "{/*0.9 BV exits}" at first BVexit, first BVy+BVup1-1 center
set arrow 8 from first BVexit, first BVy+BVup1 to BVexit, first BVy+BVup2 head
plot "Woy-Woy-1985-test-brake-van-TC3.txt" using 1:3 title "3, air temperature alongside brake van 2 m up on LH side" with points pt 1  pointsize 0.5 lc "blue" lw 1 axes x1y1, \
"Woy-Woy-1985-test-brake-van-TC4.txt" using 1:3 title "4, air temperature alongside brake van 4 m upon LH side" with points pt 2 ps 0.5 lc "green" axes x1y1, \
"Woy-Woy-1985-test-brake-van-TC1.txt" using 1:3 title "1, air temperature alongside brake van 2 m up on RH side" with points pt 3 ps 0.3 lc "black" lw 5 axes x1y1 , \
"Woy-Woy-1985-test-brake-van-TC2.txt" using 1:3 title "2, air temperature alongside brake van 4 m up on RH side" with points pt 4 ps 0.2 lc "red" lw 5 axes x1y1, \
"Woy-Woy-1985-test-68-km-post.txt" using 1:2 title "Ad hoc measurement: handheld temperature sensor in the tunnel near the 68 km marker plate" with points pt 5 ps 0.5 lc "yellow" lw 5 axes x1y1
