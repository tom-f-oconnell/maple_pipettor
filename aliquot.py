#!/usr/bin/env python

"""
Script to use MAPLE, with a scale and some purpose-built effectors, to aliquot
out liquids by mass with a serological pipette.
"""

from __future__ import print_function
from __future__ import division

import os
import sys
import time
from datetime import datetime

import numpy as np
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
    move_gripper_servo(robot, 2.65) # 2.7


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
        # TODO calc offset from full bounds anyway prob, and just adjust based
        # on these bounds?
        start_letter = 'D'
        end_letter = 'J'
        start_num = 2
        end_num = 9

        # TODO could switch them... (if making kwarg of init)
        assert start_letter <= end_letter
        assert start_num <= end_num

        self.letters = [chr(x) for x in
            range(ord(start_letter), ord(end_letter) + 1)][::-1]
        self.nums = list(range(start_num, end_num + 1))

        # trying to only visit interior regions, since the flaps are less likely
        # to flip the vial when replacing it, since they are supported on all
        # sides, and thus less likely to get bent
        n_cols = len(self.letters) #6
        n_rows = len(self.nums) #7

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
            anchor_spacing, loaded=True,
            calibration_approach_from=calibration_approach_from)

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


    def coord_label(self, i, j):
        return self.letters[i], self.nums[j]


if __name__ == '__main__':
    weigh_aliquots = True
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
    correction_y = 0
    vialbox_offset = (754 + correction_x, -14.5 + correction_y)
    vialbox = ScintillationVialBox(robot, vialbox_offset, vial_grip_height)
    # TODO delete
    '''
    wrong_ijs = [(n // vialbox.n_cols, n % vialbox.n_rows) for n in range(20)]
    wrong_lines = [', {0}, {1[0]}, {1[1]}, , '.format(n,
        vialbox.coord_label(i, j)) for n, (i, j) in enumerate(wrong_ijs)]
    print('\n'.join(wrong_lines))
    ijs = [(n // vialbox.n_rows, n % vialbox.n_rows) for n in range(20)]
    lines = [', {0}, {1[0]}, {1[1]}, , '.format(n,
        vialbox.coord_label(i, j)) for n, (i, j) in enumerate(ijs)]
    print('correct:')
    print('\n'.join(lines))
    import ipdb; ipdb.set_trace()
    '''
    #

    # TODO TODO probably refactor calibration_approach_from into just
    # approach_from, which is used in calibration and during motions, for
    # best applicability of calibration, or for controlling backlash w/o
    # calibration. w/ separate flag to calibrate?

    # In hopes that after controlling backlash a little, the gripper can be
    # centered on each vial a little better, maybe making things reliable
    # enough. Using a corner for the most consistent approach directions.
    approach_from = vialbox.anchor_center(0, 0)

    release_vial(robot)
    robot.moveZ2(0)

    syringepump_xy = (632, 179)
    syringepump_z = 22
    if weigh_aliquots:
        pump_xy_approach = [
            (syringepump_xy[0], 160)
        ]
    else:
        pump_xy_approach = [
            (660, 160),
            (syringepump_xy[0], 160)
        ]

    # TODO should err if pump is off (right now, seems to still be able to open
    # serial connection?)
    pump = wpi_al1000.AL1000(port='/dev/ttyUSB1')

    cc_str = input('Size of syringe in mL (default=60)? ')
    cc = 60
    if len(cc_str) != 0:
        cc = int(cc_str)

    if cc == 60:
        print('Assuming the 60mL syringe is a BD plastic syringe!')
        family = 'B-D'
    elif cc == 20:
        print('Assuming the 20mL syringe is a Norm-Ject plastic syringe ' +
            '(marked HSW)!')
        family = 'NORM-JECT'

    capacity_str = input('What volume of pfo (mL) is in the syringe (round ' +
        'DOWN) (default=syringe capacity)? ')
    if len(capacity_str) != 0:
        capacity = float(capacity_str)
        pump.capacity = capacity

    pump.set_syringe(family=family, cc=cc)
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
        drop_wait_s = 20
        print('Waiting {} seconds for drops to fall... '.format(drop_wait_s),
            end='')
        sys.stdout.flush()
        time.sleep(drop_wait_s)
        print('done')

        robot.moveXY(pump_xy_approach[-1])
        #zvial_travel = robot.z2_to_worksurface - 2 * vial_grip_height - 3
        # (to simplify things for now)
        zvial_travel = 0
        robot.moveZ2(zvial_travel)
        for xy in pump_xy_approach[:-1][::-1]:
            robot.moveXY(xy)

    if weigh_aliquots:
        from mettler_toledo_device import MettlerToledoDevice
        scale = MettlerToledoDevice(port='/dev/ttyUSB0')

        # TODO some scale command to automate this? setting to make it not
        # sleep?
        print('Tap the scale to wake it up, if it is not already.')
        #
        zeroed = False
        # TODO this doesn't seem to work if we can't wake the scale...
        print('Waiting for stable weight to zero... ', end='')
        sys.stdout.flush()
        while not zeroed:
            zeroed = scale.zero_stable()
        print('done')

        scale_xy = (632, 2)
        # 23 would stick sometimes
        scale_z = 23

        def weigh_vial():
            """Returns vial weight in grams. Assumes start at safe Z height.
            """
            # just to be safe. could delete later.
            robot.moveZ2(0)
            #
            robot.moveXY(scale_xy)
            robot.moveZ2(scale_z - 0.5)

            release_vial(robot)
            robot.moveZ2(0)
            time.sleep(1)
        
            ret = None
            print('Waiting for stable weight... ', end='')
            sys.stdout.flush()
            while ret is None:
                # 2-list w/ float value and str repr of unit (e.g. 'g')
                # None if weight is not stable.
                ret = scale.get_weight_stable()
            print('done')

            weight = ret[0]
            assert ret[1] == 'g', \
                'expected scale units in grams (got {})'.format(ret[1])

            robot.moveZ2(scale_z)
            grip_vial(robot)

            #zvial_travel = robot.z2_to_worksurface - 2 * vial_grip_height - 3
            # (to simplify things for now)
            zvial_travel = 0
            robot.moveZ2(zvial_travel)

            return weight

    # TODO delete
    '''
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
                print(i, j)
                ix, jy = vialbox.anchor_center(i, j)
                print(ix, jy)
                # To keep backlash more consistent.
                robot.moveXY(approach_from)
                robot.moveXY((ix,jy))
                import ipdb; ipdb.set_trace()
                vialbox.get_indices(i, j)

                #robot.moveXY(approach_from)
                vialbox.put_indices(i, j)
                import ipdb; ipdb.set_trace()
    '''

    # rates as low as 2 have caused slipping in my use case
    # (maybe also 1.5?)
    max_rate = 1.5
    rate = 1.0
    rate_str = input('Pumping rate (mL/min) (default={}, max={})? '.format(
        rate, max_rate))
    if len(rate_str) != 0:
        rate = float(rate_str)
        if rate < 0 or rate > max_rate:
            raise ValueError('rate must be between 0 and {}'.format(max_rate))

    pump.set_rate(rate, unit='MM')
    remote_rate = pump.get_rate()
    print('Using rate of {} mL/min'.format(remote_rate))

    vol_str = input('Target volume (mL) (default=2.00)? ')
    # Just pressing Enter yields and empty string (at least in Python 2)
    if len(vol_str) == 0:
        vol_ml = 2.0
    else:
        # TODO also err if out of some range / too many sig figs?
        vol_ml = float(vol_str)

    cv = -0.02
    cv_str = input('Volume correction (mL, added to target volume) ' +
        '(default={})? '.format(cv))
    if len(cv_str) != 0:
        cv = float(cv_str)
    vol_ml = vol_ml + cv

    max_aliquots = vialbox.n_cols * vialbox.n_rows
    # TODO TODO maybe make the default the max given vol in syringe?
    n_str = input('Number of aliquots (default=20)? ')
    n_aliquots = 20
    if len(n_str) != 0:
        n_aliquots = int(n_str)
        if n_aliquots < 0:
            raise ValueError('number of aliquots must be positive')
        elif n_aliquots > max_aliquots:
            raise ValueError('number of aliquots can not exceed # of reachable '
                + 'vials ({})'.format(max_aliquots))

    empty_vial_weights = np.empty((vialbox.n_cols, vialbox.n_rows))
    empty_vial_weights[:] = np.nan
    pfo_weights = np.empty((vialbox.n_cols, vialbox.n_rows))
    pfo_weights[:] = np.nan

    if weigh_aliquots:
        csv_file = 'aliquot_masses.csv'
        print('Will write aliquot weight data to {}'.format(csv_file))
        run_start_timestamp = datetime.now()
        if not os.path.exists(csv_file):
            header = 'run_start_timestamp, n, col, row, empty_vial_g, pfo_g\n'
            with open(csv_file, 'w') as f:
                f.write(header)

    # TODO TODO prompt for some amount by which to modify volume
    # (probably additively) to correct for last drop

    # TODO TODO calculate and print total time program will take

    # TODO delete after getting to save state
    start_n_str = input('Last completed aliquot # of previous run ' +
        '(leave blank to start program program from beginning)? ')
    start_n = 0
    if len(start_n_str) != 0:
        # TODO maybe just get max from aliquot_masses.txt?
        start_n = int(start_n_str) + 1
    #
    for n in range(start_n, n_aliquots):
        print('Aliquot #{}'.format(n))
        i = n // vialbox.n_rows
        j = n % vialbox.n_rows
        col_letter, row_num = vialbox.coord_label(i, j)
        print('{}{} (i={}, j={})'.format(col_letter, row_num, i, j))

        # To keep backlash more consistent.
        robot.moveXY(approach_from)
        # Grips a vial and moves to working height.
        vialbox.get_indices(i, j)

        if weigh_aliquots:
            empty_vial_g = weigh_vial()
            print('empty vial weight:', empty_vial_g)
            empty_vial_weights[i, j] = empty_vial_g

        # TODO maybe make a platform for vial so the manipulator can do either
        # things while (slow) pump is pumping?
        fill_vial(vol_ml)

        if weigh_aliquots:
            full_vial_g = weigh_vial()
            pfo_g = full_vial_g - empty_vial_g
            print('pfo weight: {} g'.format(pfo_g))
            pfo_weights[i, j] = pfo_g

            # TODO set err thresh based on some relative deviation from expected
            # mass, given density of pfo?

            with open(csv_file, 'a') as f:
                f.write('{}, {}, {}, {}, {}, {}\n'.format(run_start_timestamp,
                    n, col_letter, row_num, empty_vial_g, pfo_g))

        # To keep backlash more consistent.
        robot.moveXY(approach_from)
        vialbox.put_indices(i, j)
    
    # So box / scale can be picked up without the traveling part of the robot
    # getting in the way.
    outoftheway_xy = (425, 0)
    robot.moveZ2(0)
    robot.moveXY(outoftheway_xy)

