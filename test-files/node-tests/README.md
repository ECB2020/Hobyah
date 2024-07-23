# Node tests

The files in this folder are test files for Hobyah's junction
calculation routines (Celvel2, Celvel3, Celvel4, Celvel5 and
Celvel6).
They test every combination of tunnel ends meeting at nodes, with
both flow directions.  Each tunnel has unique sectypes and custom
fixed pressure loss factors at the ends.  The intent of generating
these files was to check that the correct variable names are used
in every part of the code - it is really easy to accidentally use
the pressure loss factor for tunnel 3 (zeta_bf3) in the fourth tunnel
connecting at the junction instead of the correct one (zeta_bf4).

Runs exist for flow in both directions in every branch, as follows:
 * Two way branches (the "ok-024" series - two files with four models each)
 * Three way branches (the "ok-025" series - 16 files with one model each)
 * Four way branches (the "ok-026" series - 32 files)
 * Five way branches (the "ok-027" series - 64 files)
 * Six way branches (the "ok-028" series - 128 files)

The test is to run all the files then compare groups of printouts.

Two sets of runs were made:
1) One to check the correctness of the Fortran code in routines
   TwoWayMoC2a, TwoWayMoC3a, TwoWayMoC4a, TwoWayMoC5a and TwoWayMoC6a
   in the "compressible.f95" module.
2) One to check the correctness of their Python equivalents TwoWayMoC2b,
   TwoWayMoC3b, TwoWayMoC4b, TwoWayMoC5b and TwoWayMoC6b in Hobyah.py.

All gave matching results, indicating that the correct calculations are
being used regardless of the orientation of the tunnels at the nodes.
