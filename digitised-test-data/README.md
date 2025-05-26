# Pressure scans

The files in this folder are scanned data from graphs of pressure vs time and velocity vs time measured during full-scale tests of trains passing through rail tunnels.  The data that has been digitised is as follows:
 * Data from graphs of pressures at sensors in the tunnels as one or two trains pass through the tunnels.
 * Data from pressures attached to the trains as they pass through the tunnels.
 * Data from graphs of velocities at sensors in the tunnels as trains pass through the tunnels.
a from papers at three BHRA International Symposia on the Aerodynamics and Ventilation of Vehicle Tunnels (ISAVVT) are included: the second conference (1976), the third (1979) and the fourth (1982).  Details of the tests and the measured data are given in the files.  The data were all recorded in the Patchway Old tunnel, Milford tunnel, Stanton tunnel and Chipping Sodbury tunnel (all in England, using various British Rail train consists).


There are seven types of file in this folder:

1) .pdf files.  These display graphs of the digitised data overlaid on the scanned images to check for close fit.  These are the first files you should look at, as they are part of this github repository's Quality Assurance evidence.  The .pdf files also record the empirical data used in any calculations that the papers' authors published.

2) .ods files.  These are spreadsheet files that can be loaded into a spreadsheet program such as LibreOffice Calc or Excel and have the raw data taken from WebPlotDigitizer (see below) and show how that data was converted into the data in the .txt files (see below).  They also record the details of the tests given in the source report/technical paper.

3) .png files.  These are image files of the pages from technical papers/reports that have full-scale test data of interest.

4) .txt files of the data in csv (comma separated value) format.  These are the data in a form that a plotting program like Hobyah, gnuplot or Python's matplotlib module can read easily.  These also hold details of the tests (in gnuplot commments).

5) .txt files with Hobyah plotting commands that generated the pdf files mentioned above.  Each time a large enough discrepancy between the image and the digitised data was spotted, the digitised data was investigated and (if necessary) adjusted or redigitised.

6) .tar files.  These are WebPlotDigitizer project files.  .Tar files are an old Unix compressed file format that is similar to - but not compatible with - the zip file format.  They contain the image that was digitised, a JSON file containing the graph scaling, and the digitised data and a JSON command file for WebPlotDigitizer.   WebPlotDigitizer is available at https://automeris.io and these files can be loaded into it and examined.  Linux and macOS can uncompress .tar files to let you see their contents, as can the 7-Zip utility on Windows.

7) .xlsx files.  These are spreadsheet files that can be loaded into Excel or LibreOffice Calc.  They are derived from the .ods files and may have slightly differences from them (mostly formatting, although I did notice that the files' keywords are messed up compared to the keywords in the .ods files).  The .ods files are the originals: if there are any differences between the .ods files and the .xlsx files, the data in the .ods files should be used.

Anyone reading this document is free to use these data for verifying the calculations of programs that calculate pressures/velocities in tunnels due to moving trains.  If the data I digitised are used in your technical papers, a mention of this github repository in your paper as the source would be appreciated.

Updates to the contents of this folder will be made occasionally as new Figures are scanned and put through the QA process of comparing the digitised data to the images that the digitised data came from.  This workstream (digitising full-scale test data from technical reports and technical papers) is of secondary importance now that I've scanned the Figures in these four technical papers, but occasional updates will be made.

Finally, any errors you find in the digitised data are entirely my fault: no errors should be attributed to the authors of the original papers.  I would appreciate being advised of any errors that I have missed, whether the error is in the digitised data or in the empirical data recorded in the files.


Ewan Bennett (ewanbennett@fastmail.com).
