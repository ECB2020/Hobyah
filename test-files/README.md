# Hobyah test files

The files in this folder are Hobyah input files (.txt files) that run calculations, generate output in text or .pdf format, and (optionally) write SES input files.

Other files in this folder are ancillary files.  Ancillary files are could be:
  * .csv files with data that a Hobyah input file needs (test data, fan curves),
  * .png files that a Hobyah "image" block imports,
  * .sbn files (binary files with SES output written by SESconv.py) that a Hobyah input file plots from and
  * .hbn files (binary files with Hobyah output written by Hobyah.py) that a Hobyah input file plots from,
  * .pdf files that a Hobyah run generates and
  * .ses or .INP files that a Hobyah run generates from a Hobyah geometry.

The Hobyah test files all start with "ok-" and a three-digit number ("ok-001" to "ok-049" and (optionally) a descriptive phrase.

The list below describes each test file's purpose.

ok-001  File with the minimum valid input.
ok-002  File with the minimum valid input and comments in the body.
ok-003  File with no comments at the top of the file.
ok-004  File checking that there is no conflict between sub-blocks.
ok-005  File with the minimum valid entries to run a calculation.
ok-006  File with all the valid entries in the "settings" block.
ok-007  File with a "files numbered" block with plotting from SES
        runs, showing every plotted property and every curve type
        (profile, transient etc.).  Generates Figures for the manual
        in the sections describing plots from SES.  Likely to be one
        of the most referenced example files for anyone using Hobyah
        to plot from SES, because it has examples of all SES plots.
ok-008  File with a "files twosyllables" block with plotting from an
        SES run.
ok-009  Test file that is a general scratchpad for development.
ok-010  File that generates the simple example of a road tunnel in
        Chapter 1 of the User Manual.
ok-011  File that uses all the capabilities of the "begin image" block.
ok-012  File that shows how to use the "begin timeloop" block and shows
        train icons and jet fan icons.
ok-013  File that calculates in a short, simple tunnel with a pressure
        difference at one end.  Originally developed in conjunction
        with spreadsheet calculation MoC-simple-021.ods.
ok-014  File that calculates in a long tunnel.  Used to test the time
        saved by various optimisations or shortcuts.
ok-015  Files (six of them, 015a to 015f) that test the logic of
        choosing/calculating different friction factors.
ok-016  Files (four of them, 016a to 016d) that test the logic of fixed
        velocity at the back portal and the forward portal.  Different
        transient behaviour but the same steady-state behaviour.
ok-017  Files (four of them, 017a to 017d) that test the logic of fixed
        volume flow at the back portal and the forward portal.  Different
        transient behaviour but the same steady-state behaviour.
ok-018  File that compares three simple tunnels that all end up at the
        same air velocity.  One has fixed pressure at a portal, one
        has fixed velocity at a portal, one has fixed volume flow at
        a portal (the latter two use the same calculation logic as the
        volume flow is turned into a velocity after being read in).
ok-019  File that tests changes of sectype, the placement of pressure
        loss factors in different locations and the absence of pressure
        loss factors.  Was used to develop the plotting of profiles at
        fixed time.  The file contains an incompressible calc of the
        cases, which matches near as dammit.
ok-020  File used (in tandem with 021) to develop error messages when
        the MoC calculation fails.  Used to develop Figure 7.1 in
        the manual.
ok-021  File used (in tandem with 020) to develop error messages when
        the MoC calculation fails.  Used to develop Figure 7.1 in
        the manual.
ok-022  File used to compare a simple tunnel with friction and pressure
        differences to a spreadsheet calc.  In the "verification" folder,
        not the "test-files" folder.
ok-023  File used to develop the "begin timeloop" block.
ok-024  Files used to verify the calculations at a two-way junction
        (two files each with four types of connection).  In the
        "node-tests" sub-folder.
ok-025  Files used to verify the calculations at three-way junctions
        (16 files).  In the "node-tests" sub-folder.
ok-026  Files used to verify the calculations at four-way junctions
        (32 files).  In the "node-tests" sub-folder.
ok-027  Files used to verify the calculations at five-way junctions
        (64 files).  In the "node-tests" sub-folder.
ok-028  Files used to verify the calculations at six-way junctions
        (128 files).  In the "node-tests" sub-folder.
ok-029  File used to develop how fan characteristics work, putting fans
        in tunnels and plotting from fans.
ok-030  File used to develop fan characteristics/fan behaviour in US
        units.
ok-031  File with a contrived system that has three fans in series
        interacting with each other with one fan going into reverse
        flow and another fan being pushed into freewheeling mode.
        A teaching tool for anyone trying to explain the behaviour of
        fans in series.
ok-032  File with a contrived system that has three fans in parallel
        interacting with each other.  One fan doesn't make it over the
        stall hump.  A teaching tool for anyone trying to explain the
        behaviour of fans in parallel and why stall humps in fan
        characteristics matter.
ok-033  Example of how to get around the "you can't have more than
        six tunnels at a junction" restriction.
ok-034  File to test the processing of warning messages from the
        scipy routines that calculate at junctions.  Has fans and
        their isolation dampers.
ok-035  File to test the setting of train properties.  A work in
        progress.
ok-036  File to test the placing and movement of trains in routes.
        A work in progress.
ok-037  A file to develop the "begin tunnelclones" block and the "joins"
        keyword in the "begin tunnel" block.
ok-038  A simplified model of the Channel Tunnel (a rail tunnel from
        Kent in England to Pas-de-Calais in France).  Written mostly to
        have a large calculation (two 50 km running tunnels with 193
        pressure relief ducts, ventilation system (SVS only) at
        Shakespeare Cliff and Sangatte) that takes a lot of time to run.
        Also a showcase of how useful the "tunnelclones" block and the
        "joins" keyword are.
ok-039  File to develop the setting of stationary traffic in routes
        and turn the traffic into body forces in the tunnels that pass
        through those routes.
ok-040  File to develop the setting of moving traffic in routes, and
        turn the traffic into body forces in the tunnels that pass
        through those routes.
ok-041  File to verify the transient calculation of airflow in a simple
        tunnel against an incompressible spreadsheet calculation and
        an incompressible SES calculation.  In the "verification"
        folder, not the "test-files" folder.
ok-042  File used to verify the setting of traffic and test the
        mechanism by which traffic affects airflow (it is a body force
        in cells, like friction; not a pressure change tied to a point,
        like a fan).  The file has a block of stationary traffic that
        starts and stops at gridpoints in one tunnel and a block of
        stationary traffic that starts and stops halfway between
        gridpoints.
ok-043  A copy of "ok-042" with cells half the size of those in "ok-042",
        for an investigation into mass flow imbalances.
ok-044  A copy of "ok-042" with cells one-fifth the size of those in
        "ok-042", for an investigation into mass flow imbalances.
ok-045  File used to verify that the calculation of stationary traffic
        is correct, comparing it to hand calculations.
ok-046  File used to develop the definitions of jet fans.
ok-047  File used to illustrate the difference in pressure profiles
        between jet fans that cause a pressure rise over a long distance
        downwind of the fan and jet fans that cause a step-change in
        pressure at the location of the fan.
ok-048  A file showing the effect of making jet fan pressure rises step
        changes or spreading the rise over a distance along the tunnel.
        A work in progess for verifying jet fans.
ok-049  File that writes a complex SES geometry (75 sections) from a
        simple Hobyah geometry (four mainline tunnels and 23 cloned
        cross-passages).
