#!/usr/bin/env python

"""
Script to use MAPLE, with a scale and some purpose-built effectors, to aliquot
out liquids by mass with a serological pipette.
"""

from __future__ import print_function
from __future__ import division

import os
import sys

import maple
import maple.robotutil
import maple.module

import wpi_al1000


try:
    input = raw_input
except NameError:
    pass


def move_gripper_servo(robot, s_position):
    """
    Supposedly S5 is fully to the left and S10 is fully to the right...
    So how is S0 "off"? Less than 5? More than 10? Interpretation of the #?

    According to reprap docs: "`Snnn` Angle or microseconds"

    Empirically:
    S2.7 seems about fully open (2.5 strains a little)
    S11.1 seems most closed, non-strained, position w/ (1/16"?) Viton pads
    S11.25 will strain them a little

    Requires different Smoothieware configuration than default MAPLE.
    Use smoothie_config in this repository.
    """
    # TODO add trailing newline in sendSyncCmd/sendCmd automatically
    cmd = 'M280 S{}\n'.format(s_position)
    robot.smoothie.sendSyncCmd(cmd)


def grip_vial(robot, pos=4.3):
    # 4.3 might help keep the vial slightly straigher than 4.5?
    # it is definitely a little looser
    move_gripper_servo(robot, pos) #, 4.3) #4.5)
    # TODO min delay that is appropriate?
    robot.dwell_ms(1000)


def release_vial(robot):
    move_gripper_servo(robot, 2.7)


# TODO see choice module implementation of array subclass, to see whether i
# changed the api
class ScintillationVialBox(maple.module.Array):
    """
    """
    def __init__(self, robot, offset, vial_grip_height,
        calibration_approach_from=None, verbose=False):
        """
        #vial_grip_height: how high up from worksurface vial should be gripped,
        #    if vial were resting on worksurface
        vial_grip_height: defined w/ 0 as home point on Z2, and positive going
            down, now; for simplicity.
        """
        gripper_working_height = vial_grip_height
        # TODO TODO TODO check that n_rows is referring to the Y (towards/away
        # me) axis
        '''
        n_cols = 10
        # Looks like at most 9 will be reachable, with box against close
        # MAPLE support. Maybe w/ lower-profile Z slide / gripper, all would be.
        n_rows = 9
        '''
        # trying to only visit interior regions, since the flaps are less likely
        # to flip the vial when replacing it, since they are supported on all
        # sides, and thus less likely to get bent
        n_cols = 8
        n_rows = 7

        # The taller two edges of the box are 64mm.
        # TODO how did i come to (100, 100, 40)? mm, right? (same w/ (5,5) for
        # to_first_anchor)
        full_box_dim = 290
        extent = (
            (n_cols / 10) * full_box_dim,
            (n_rows / 10) * full_box_dim,
            64
        )
        # TODO default to extent (- 2*border) divided by cols/rows
        # TODO maybe w/ a border variable (not sure it's reasonable to assume
        # that would be zero, given how i'm using extent as actual size of thing
        # in workspace)
        anchor_spacing = extent[0] / n_cols
        # TODO TODO have this default to assuming the grid centers are symmetric
        # about the module extent center (not z of course), in maple Array def
        to_first_anchor = anchor_spacing / 2.0

        super(ScintillationVialBox, self).__init__(robot, offset, extent,
            gripper_working_height, n_cols, n_rows, to_first_anchor,
            anchor_spacing, calibration_approach_from=calibration_approach_from)

        # TODO remove this / any need for this in maple module, if there still
        # is any
        self.z0_working_height = 45.0

        # TODO use self.full for vial presence or whether vial has been filled
        # or what?
        # support less than full box? support different amounts in some?
        # separate state variables for vial presence and fill status?


    # TODO TODO delete the this testing logic / move into maple
    # (just disable z? i have one other comment on this somewhere)
    testing = False
    #testing = True
    test_buffer = 20
    def get(self, xy, ij):
        """Moves to a vial and picks it up.
        """
        # TODO TODO factor working distance z travels into parent class
        # (otherwise little point in the shared instance variable)
        # TODO rename latter to z2_.. in maple
        #zw = self.robot.z2_to_worksurface - self.flymanip_working_height
        # (for simplicity, using smoothie coords now)
        zw = self.flymanip_working_height
        if self.testing:
            zw -= self.test_buffer
            zw = max(zw, 0)

        self.robot.moveXY(xy)

        # TODO assert we aren't carrying a vial or something?
        # do something like that in array by default?
        # (should work same way w/ flies)
        # To open grippers so they can fit around the vial.
        release_vial(self.robot)

        self.robot.moveZ2(zw)

        grip_vial(self.robot)

        # Although all get/put calls get flanked by moving effectors to travel
        # height, need to move higher when we are holding a vial, as otherwise
        # it would crash into the box when moving.
        #zvial = zw - self.flymanip_working_height - 3
        # (to simplify things for now)
        zvial = 0
        self.robot.moveZ2(zvial)


    def put(self, xy, ij):
        """Moves to a (presumed empty) space in the box and releases the vial.
        """
        #zw = self.robot.z2_to_worksurface - self.flymanip_working_height - 2
        # (for simplicity, using smoothie coords now)
        zw = self.flymanip_working_height - 1
        if self.testing:
            zw -= self.test_buffer
            zw = max(zw, 0)

        self.robot.moveXY(xy)
        self.robot.moveZ2(zw)
        release_vial(self.robot)
        # also just using absolute smoothie coords for simplicity for now,
        # rather than rely on auto return (current offsets, like z2_to_w...
        # are wrong and would cause crashes)
        self.robot.moveZ2(12)


if __name__ == '__main__':
    print('Vialbox should be oriented so the side facing you reads A-J')

    # TODO is this not the default config? just defer to whatever default
    # settings there are, whether this file or something else?
    robot = maple.robotutil.MAPLE(os.path.join(maple.__path__[0], 'MAPLE.cfg'),
        enable_z0=False, enable_z1=False, z2_has_crash_sensor=False)#, home=False)
    # TODO TODO put these hardcoded offsets in some config? some override config
    # where central config still does most stuff?
    # TODO provide defaults in maple config even? or maybe have 0 at top if 
    # none provided? or have that as another mode?

    # TODO TODO replace all other places that use "if robot is None"
    # check for dry run w/ some mock robot class / dryrun flag in robotutil
 
    # TODO are the lhs and vial_grip_height really interacting as i want?
    # shouldn't changing vial_grip_height not affect where worksurface is
    # defined?
    vial_grip_height = 59.5
    # 60 is about as far down as i want the z axis to go
    # TODO try to only go to to 58 intead of 60 (vial_grip_height is subtracted
    # off when computing working height for gripper)? may need to change some
    # other values to avoid limit when going up.
    # 62 def holds vial a little straighter than 60 (w/ vial_grip_height=58),
    # but pushes on box edges a little. any less work?
    # 61 doesn't work that well.
    #robot.z2_to_worksurface = 60 + vial_grip_height
    # currently just used for automatic return in module get_/put_
    robot.z2_to_worksurface = 118

    correction_x = 0
    correction_y = 17
    vialbox_offset = (690 + 29 + correction_x, -14.5 + correction_y)
    vialbox = ScintillationVialBox(robot, vialbox_offset, vial_grip_height)

    # TODO TODO probably refactor calibration_approach_from into just
    # approach_from, which is used in calibration and during motions, for
    # best applicability of calibration, or for controlling backlash w/o
    # calibration. w/ separate flag to calibrate?

    # In hopes that after controlling backlash a little, the gripper can be
    # centered on each vial a little better, maybe making things reliable
    # enough. Using a corner for the most consistent approach directions.
    approach_from = vialbox.anchor_center(0, 0)

    '''
    syringepump_xy = (632, 175)
    syringepump_z = 22
    pump_xy_approach = [
        (660, 160),
        (syringepump_xy[0], 160)
    ]
    pump = wpi_al1000.AL1000()

    cc_str = input('Size of syringe in mL (default=60)? ')
    if len(cc_str) == 0:
        cc = 60
    else:
        cc = int(cc_str)

    if cc == 60:
        print('Assuming the 60mL syringe is a BD plastic syringe!')
        family = 'B-D'
    elif cc == 20:
        print('Assuming the 20mL syringe is a Norm-Ject plastic syringe ' +
            '(marked HSW)!')
        family = 'NORM-JECT'

    pump.set_syringe(family=family, cc=cc)
    # TODO delete. for testing.
    pump.capacity = 5.0
    #
    def fill_vial(vol_ml):
        """Moves vial under syringe pump output.
        Assumes Z2 is at appropriate travel height already.
        """
        have_vol = pump.can_dispense(vol_ml)
        if not have_vol:
            input('Re-fill syringe and press Enter to continue...')
            pump.clear_vol_disp()

        for xy in pump_xy_approach:
            robot.moveXY(xy)
        # Only doing this after gripper is no longer over box,
        # as a good height here might crash into box.
        robot.moveZ2(syringepump_z)
        robot.moveXY(syringepump_xy)
        
        pump.dispense(vol_ml)

        robot.moveXY(pump_xy_approach[-1])
        #zvial_travel = robot.z2_to_worksurface - 2 * vial_grip_height - 3
        # (to simplify things for now)
        zvial_travel = 0
        robot.moveZ2(zvial_travel)
        for xy in pump_xy_approach[:-1][::-1]:
            robot.moveXY(xy)
    '''

    # TODO delete
    """
    robot.moveZ2(0)
    for x in range(vialbox.n_cols // 2):
        for y in range(vialbox.n_rows // 2):
            for corner in range(4):
                if corner == 0:
                    i = x
                    j = y
                elif corner == 1:
                    i = x
                    j = vialbox.n_rows - y - 1
                elif corner == 2:
                    i = vialbox.n_cols - x - 1
                    j = y
                elif corner == 3:
                    i = vialbox.n_cols - x - 1
                    j = vialbox.n_rows - y - 1
                print (i, j)
                # To keep backlash more consistent.
                robot.moveXY(approach_from)
                vialbox.get_indices(i, j)
                #import ipdb; ipdb.set_trace()

                fill_vial(2.0)

                robot.moveXY(approach_from)
                vialbox.put_indices(i, j)
                #import ipdb; ipdb.set_trace()
    """
    weigh_aliquots = True
    if weigh_aliquots:
        from mettler_toledo_device import MettlerToledoDevice
        scale = MettlerToledoDevice(port='/dev/ttyUSB0')
        print(scale.get_balance_data())
        #import pdb; pdb.set_trace()
        scale_xy = (632, 135)
        # TODO find a good value
        scale_z = 28

        def weigh_vial():
            """Returns vial weight in grams. Assumes start at safe Z height.
            """
            robot.moveXY(scale_xy)
            robot.moveZ2(scale_z)

            # TODO release vial slightly above scale (then move that amount
            # down before gripping it again)?
            release_vial(robot)
        
            ret = None
            print('Waiting for stable weight... ', end='')
            sys.stdout.flush()
            while ret is None:
                # 2-list w/ float value and str repr of unit (e.g. 'g')
                # None if weight is not stable.
                ret = scale.scale.get_weight_stable()
            print('done')

            weight = ret[0]
            assert ret[1] == 'g', \
                'expected scale units in grams (got {})'.format(ret[1])

            grip_vial(robot)

            #zvial_travel = robot.z2_to_worksurface - 2 * vial_grip_height - 3
            # (to simplify things for now)
            zvial_travel = 0
            robot.moveZ2(zvial_travel)

            return weight

    vol_str = input('Target volume (mL) (default=2.00)? ')
    # Just pressing Enter yields and empty string (at least in Python 2)
    if len(vol_str) == 0:
        vol_ml = 2.0
    else:
        # TODO also err if out of some range / too many sig figs?
        vol_ml = float(vol_str)

    max_aliquots = vialbox.n_cols * vialbox.n_rows
    n_str = input('Number of aliquots? ')
    n_aliquots = int(n_str)
    if n_aliquots < 0:
        raise ValueError('number of aliquots must be positive')
    elif n_aliquots > max_aliquots:
        raise ValueError('number of aliquots can not exceed # of reachable ' +
            'vials ({})'.format(max_aliquots))

    import pdb; pdb.set_trace()

    for i in range(n_aliquots):
        # Grips a vial and moves to working height.
        vialbox.get_next()

        # TODO if weigh_aliquots, take vial to scale and measure it first
        # and again after
        if weigh_aliquots:
            empty_vial_g = weigh_vial()

        # TODO maybe make a platform for vial so the manipulator can do either
        # things while (slow) pump is pumping?
        # TODO maybe don't do final turn in moving away from pump when going to
        # scale (assuming weight point is similar enough in X to not crash)
        fill_vial(vol_ml)

        if weigh_aliquots:
            full_vial_g = weigh_vial()
            pfo_g = full_vial_g - empty_vial_g

        # TODO TODO TODO get_next -> put_next work as i've implemented it?
        vialbox.put_next()

