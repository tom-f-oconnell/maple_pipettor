#!/usr/bin/env python

"""
Script to use MAPLE, with a scale and some purpose-built effectors, to aliquot
out liquids by mass with a serological pipette.
"""

from __future__ import print_function
from __future__ import division

import os
#
import time
#

import maple
import maple.robotutil
import maple.module


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
    if robot is not None:
        # TODO add trailing newline in sendSyncCmd/sendCmd automatically
        cmd = 'M280 S{}\n'.format(s_position)
        robot.smoothie.sendSyncCmd(cmd)


def fully_open_gripper(robot):
    move_gripper_servo(robot, 2.7)


def grip_vial(robot):
    move_gripper_servo(robot, 4.5)
    robot.dwell_ms(1000)
    # TODO robot.dwell_ms here?


def release_vial(robot):
    #move_gripper_servo(robot, 3)
    move_gripper_servo(robot, 2.7)


# TODO see choice module implementation of array subclass, to see whether i
# changed the api
class ScintillationVialBox(maple.module.Array):
    """
    """
    def __init__(self, robot, offset, vial_grip_height,
        calibration_approach_from=None, verbose=False):
        """
        vial_grip_height: how high up from worksurface vial should be gripped,
            if vial were resting on worksurface
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
        n_rows = 8

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


    def get(self, xy, ij):
        """
        """
        # TODO TODO factor working distance z travels into parent class
        # (otherwise little point in the shared instance variable)
        # TODO rename latter to z2_.. in maple
        zw = self.robot.z2_to_worksurface - self.flymanip_working_height
        if self.robot is not None:
            # TODO delete
            print('MOVING TO', xy)
            #
            self.robot.moveXY(xy)

            # TODO assert we aren't carrying a vial or something?
            # do something like that in array by default?
            # (should work same way w/ flies)
            # To open grippers so they can fit around the vial.
            #self.robot.dwell_ms(500)
            release_vial(self.robot)
            #self.robot.dwell_ms(500)

            # TODO delete
            print('MOVING Z2 TO', zw)
            #
            self.robot.moveZ2(zw)

        #
        #import ipdb; ipdb.set_trace()
        #
        grip_vial(self.robot)

        # Although all get/put calls get flanked by moving effectors to travel
        # height, need to move higher when we are holding a vial, as otherwise
        # it would crash into the box when moving.
        zvial = zw - self.flymanip_working_height #- 2
        # TODO delete
        print('MOVING Z2 TO', zvial)
        #
        self.robot.moveZ2(zvial)


    def put(self, xy, ij):
        """
        """
        zw = self.robot.z2_to_worksurface - self.flymanip_working_height
        if self.robot is not None:
            self.robot.moveXY(xy)
            self.robot.moveZ2(zw)

        release_vial(self.robot)


'''
# TODO maybe inherit maple.module?
class Scale:
    def __init__(self, robot, offset, port='/dev/ttyACM0'):
        from mettler_toledo_device import MettlerToledoDevice

        self.robot = robot
        self.offset = offset
        self.z0_working_height = 5.0
        # TODO rename to z2
        self.flymanip_working_height = 12.0

        self.scale = MettlerToledoDevice(port=port)
        print(self.scale.get_balance_data())


   def fill_vial(self):
        """Take a vial to the scale, and fill it to a certain mass.
        Pick it up afterwards.
        """
        zt = self.robot.z2_to_worksurface - self.extent[2]
        if self.robot is not None:
            self.robot.moveZ2(zt)

        zw = self.robot.z2_to_worksurface - self.flymanip_working_height
        if self.robot is not None:
            self.robot.moveXY(xy)
            self.robot.moveZ2(zw)

        release_vial(self.robot)

        if self.robot is not None:
            self.robot.moveZ2(zt)

        # TODO TODO fill up serological pipette

        # TODO travel back to vial

        # TODO empty (w/ some kind of control) until we hit appropriate mass

        # TODO maybe blow out extra pfo? (if would drip too much otherwise)


class StockContainer:
    def __init__(self, robot, center):
        self.robot = robot
        self.center = center
        self.z0_working_height = 5.0
        # TODO rename to z2
        self.flymanip_working_height = 12.0
        self.z_extent = 50.0


    # TODO factor something like this into another maple class of physical
    # objects w/ positions (+ heights? + travel heights?)
    def center_over(self):
        # TODO also move z2 above minimum height?
        zt = self.robot.z0_to_worksurface - self.z_extent
        if self.robot is not None:
            self.robot.moveZ0(zt)

        zw = self.robot.z0_to_worksurface - self.z0_working_height
        if self.robot is not None:
            self.robot.moveXY(center)
            self.robot.moveZ0(zw)


    def load_pipette(self):
        self.center_over()
        # TODO pulse?
        self.robot.smallPartManipAir(False)
        self.robot.smallPartManipVac(True)
        # TODO test this. need feedback?
        self.robot.dwell_ms(5000)
        self.robot.smallPartManipVac(False)
        # TODO need to pulse aftwerwards?


    def clear_pipette(self):
        self.center_over()
        self.robot.smallPartManipVac(False)
        self.robot.smallPartManipAir(True)
        self.robot.dwell_ms(3000)
        self.robot.smallPartManipAir(False)
        # TODO move back to height?
'''


if __name__ == '__main__':
    # TODO is this not the default config? just defer to whatever default
    # settings there are, whether this file or something else?
    robot = maple.robotutil.MAPLE(os.path.join(maple.__path__[0], 'MAPLE.cfg'),
        enable_z0=False, enable_z1=False, z2_has_crash_sensor=False, home=False)
    # TODO TODO put these hardcoded offsets in some config? some override config
    # where central config still does most stuff?
    # TODO provide defaults in maple config even? or maybe have 0 at top if 
    # none provided? or have that as another mode?
 
    vial_grip_height = 58
    # 60 is about as far down as i want the z axis to go
    #robot.z2_to_worksurface = 60 + vial_grip_height
    robot.z2_to_worksurface = 60 + vial_grip_height

    vialbox_offset = (690 + 29, -14.5)
    vialbox = ScintillationVialBox(robot, vialbox_offset, vial_grip_height)

    syringepump_xy = (632, 175)
    syringepump_z = 22
    pump_xy_approach = [
        (660, 160),
        (syringepump_xy[0], 160)
    ]
    def fill_vial():
        """Moves vial under syringe pump output.
        Assumes Z2 is at appropriate travel height already.
        """
        for xy in pump_xy_approach:
            robot.moveXY(xy)
        old_z = robot.currentPosition[-1]
        # Only doing this after gripper is no longer over box,
        # as a good height here might crash into box.
        robot.moveZ2(syringepump_z)
        robot.moveXY(syringepump_xy)

        ###pump.dispense(2.0)
        # TODO TODO TODO need to wait for pump to finish.
        # probably poll the pump at some interval.
        #
        robot.dwell_ms(3000)
        #

        robot.moveXY(pump_xy_approach[-1])
        zvial_travel = robot.z2_to_worksurface - 2 * vial_grip_height # - 2
        # TODO delete
        print('moving back to vial travel height:', zvial_travel)
        #
        robot.moveZ2(zvial_travel)
        for xy in pump_xy_approach[:-1][::-1]:
            robot.moveXY(xy)

    # TODO delete

    # TODO TODO this seems to hang under some conditions when program is
    # restarted after being stopped in debugging. fix if possible!
    # (other servo commands are also timing out, like in grip)
    #fully_open_gripper(robot)

    initial = True
    for i in range(vialbox.n_cols):
        for j in range(vialbox.n_rows):
            if not initial:
                vialbox.put_indices(i, j)
            else:
                initial = False
            vialbox.get_indices(i, j)

    import ipdb; ipdb.set_trace()
    vialbox.get_indices(0, 0)
    import ipdb; ipdb.set_trace()
    fill_vial()
    import ipdb; ipdb.set_trace()
    vialbox.put_indices(0, 0)
    import ipdb; ipdb.set_trace()

    #vialbox.get_indices(4, 0)

    # TODO some move_over fn / no_z flag for get_indices, for testing?
    # or just move smoothie?
    # TODO some test picking up vials and moving them / putting them back down
    vialbox.get_indices(5, 4)
    import ipdb; ipdb.set_trace()

    #

    # TODO move up / over one + put it back

    '''
    using_scale = False
    #scale = Scale()

    # (empty of empty vials)
    # TODO break on other conditions / say what needs replaced /
    # why things stopped
    while not vialbox.is_empty():
        # Grips a vial and moves to working height.
        vialbox.get_next()

        # TODO
        # Moves to syringe pump and dispenses target volume.
        # can probably leave vial gripped?


        # Moves full vial to accumulation area.

        

        # 2-list w/ float value and str repr of unit (e.g. 'g')
        # None if weight is not stable.
        #print(scale.scale.get_weight_stable())
    '''

