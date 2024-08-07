# SES files that succeed or cause simulation errors

The files in this folder are a set of input files (.ses files) and output files (.PRN and .TMP files) for SES v4.1 and offline-SES.

Most of the files were written so that the output files could be used to test the operation of SESconv.py.  A few are to verify the calculations in Hobyah.py.

The output files were fed to SESconv.py, which generated the _ses.txt files (the SES output file converted into SI units) and the .sbn files (a binary Python pickle file that can be interrogated by classSES.py).  SES output files may be dragged and dropped onto SESconv.py on Windows machines to get SESconv.py to generate its two output files.

The files use most of the features in SES v4.1, different print options, types of value (e.g. using zero to get a default value), input forms and types of output.  Many files have demonstrably incorrect input, like running a fire simulation and putting the fire in a non-fire segment (SESconv.py raises a fatal error when it processes this one).  Few of the files in this folder are suitable for basing new input files on.

The following SES input errors have specific files to trigger them because they write output files that are tricky to process:

* Input errors 32 (dud hour) and 33 (dud month), (file 057)
* Input error 125 (route ended before the last tunnel) (files 058 and 059)

The following SES simulation errors have test files (they create .TMP files in v4.1):

* Simulation error 5, thermodynamic velocity-time stability (file 055)
* Simulation error 6, fan gets overpowered by train movements (file 051)
* Simulation error 7, net train area exceeds tunnel area (file 052)
* Simulation error 8, ECZ estimate doesn't converge (file 054)

Known aspects that are not covered are:
* Permitting a non-zero amount of input errors and simulation errors (this can cause some weird stuff to happen).
* Simulation error 1 (too many trains in the calculation)
* Simulation error 2 (divide by zero)
* Simulation error 3 (math overflow)
* Simulation error 4 (more than 8 trains in the same segment)
* Simulation error 11 (bad humidity matrix)
* Simulation error 12 (bad temperature matrix)
