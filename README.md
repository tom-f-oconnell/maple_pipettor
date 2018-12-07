
### maple_pipettor

Unscrew the vacuum cup from that MAPLE effector, and screw an adapter in between
that thread (1/8" NPT in original MAPLE designs) and whatever tubing you want to
use. This could be either a thread->barb or thread->Luer adapter. Insert a Luer
lock into the custom serological pipette adapter. Run a line, with a filter in
it if you want, between the manifold and the Luer lock on the serological
pipette adapter.

Attach the serological pipette mount to the two outer, unused, mounting holes
above the vacuum cup manifold. Clamp it down on the pipette you want to use.

In place of the fly manipulator effector, attach a servo gripper, via a custom
adapter. Attach the pin normally used to control the fly manipulator vacuum to
the servo control input.

Use two 1-10K resistors to divide the 12V (any reason to divide the 12V? or just
also use the 5V for the signal too? (would probably still need some resistors,
to not just short that power supply)


The gripper is for moving scintillation vials on and off of the scale, and the
serological pipette is for filling the vials on the scale, using a stock vial
somewhere else in the workspace.

#### TODO
Should make it so the user is prompted for a target mass when `aliquot.py`
is run, or maybe allow setting the mass through configuration.

Is there appropriate supply voltage for the servo already on the breakout board
somewhere, or will I have to build that in somewhere?
Check the 5v providing power to the pressure sensor can supply the ~800mA stall
current (maybe higher at 5v rather than 6v?).

