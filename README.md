# Hobyah
A 1D tunnel ventilation calculation program and plotter.

First example to look at is "ok-032-fans-in-parallel-animation.gif" in the "documentation" folder.
Second example to look at is "ok-012-timeloop-animation.gif" in the "documentation" folder.

Read the "Hobyah-User-Guide.pdf" in the documentation folder for more details.

Main features:
  1) Builds a 1D tunnel network with area changes, pressure differences, fixed flowrates, fans, jet fans, dampers and traffic.
  2) Solves compressible isentropic flow in the network by the method of characteristics and stores the results in text and binary form.
  3) Processes SES v4.1 & OpenSES v4.3 output files, converting them to SI units and storing the contents in binary form.
  4) Plots output from Hobyah alongside output from SES and from .csv files.
  5) Generates graphs and animations of the Hobyah and SES calculations.
  6) Generates skeleton SES input files from the geometry and routes.
  7) Provides a simple incompressible flow spreadsheet.
  8) Provides two classes for manipulating the binary data.

Hobyah.py is the main program file.  It has three main tasks:
  1) It reads input files and generates a network of tunnels and adits with 1D flow properties, puts in entities like fixed pressures, fixed flowrates, abrupt area changes, fans, jet fans, dampers, moving traffic, stationary traffic and routes.  Fans can stop, start and reverse multiple times.  Dampers can open and close multiple times.  Transient flow is solved and the results are saved as text and in binary (pandas DataFrames).
  2) Generate plots of data from Hobyah binary files, SES binary files and blocks of .csv data.
  3) Generate the skeleton of an SES input file from the network of tunnels and adits built for the compressible solver.  Copy over the route profiles and, where possible, set segment stack heights from node elevations.

SESconv.py is a routine that converts SES output files in US customary units to SI units.  It writes an equivalent output file in SI units, then saves the SES output file's data in dictionaries/pandas DataFrames in a binary file.  These can be plotted from by Hobyah plot definitions.

Two Python classes are available (classHobyah.py and classSES.py).  One handles the binary file written by Hobyah.py, the other handles the binary file written by SESconv.py.  Both can be called by other programs (currently only Hobyah.py) to generate plot data along routes, plot data at a fixed location as the data evolves over time and generate new SES input files.

Generics.py, syntax.py and UScustomary.py are ancillary routines that are used by the main programs.

Compressible.f95 is a Fortran routine that carries out Hobyah's compressible calculation faster than the equivalent Python code.  It is worth using if you need to do compressible calculations fast. It is not needed if you are just plotting from SES or from .csv files.  In addition to the source code, executables are provided for Windows and Apple silicon.

"quadratics.ods" is an incompressible flow spreadsheet for a simple road tunnel (two portals, no area changes, no junctions).  The spreadsheet handles friction, jet fans, drag of moving traffic and portal pressure differences.  It was written as part of the validation work for the method of characteristics program, but may be useful in other contexts.  It has an equivalent Excel version (as Excel doesn't like .ods spreadsheets).

The suite is named after The Hobyahs, the villains in a fairy tale from my pre-school days.
