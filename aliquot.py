#!/usr/bin/env python3

"""
Script to use MAPLE, with a scale and some purpose-built effectors, to aliquot
out liquids by mass with a serological pipette.
"""

from __future__ import print_function
from __future__ import division

import os

import maple
import maple.robotutil
import maple.module
from mettler_toledo_device import MettlerToledoDevice


def move_gripper_servo(robot, angle):
    """
    Supposedly S5 is fully to the left and S10 is fully to the right...
    So how is S0 "off"? Less than 5? More than 10? Interpretation of the #?

    According to reprap docs: "`Snnn` Angle or microseconds"

    Requires different Smoothieware configuration than default MAPLE.
    Use config in this repository.
    """
    if robot is not None:
        robot.sendSyncCmd('M280 S{}'.format(


def grip_vial(robot):
    """
    """
    move_gripper_servo(robot, 60)


def release_vial(robot):
    """
    """
    move_gripper_servo(robot, 0)


class ScintillationVialBox(maple.module.Array):
    """
    """
    def __init__(self, robot, offset, position_correction=False,
            calibration_approach_from=None, verbose=False):

        gripper_working_height = 35.0
        n_cols = 10
        n_rows = 10

        extent = (100, 100, 40)
        # TODO 
        to_first_anchor = (5, 5)

        super(ScintillationVialBox, self).__init__(robot, offset, extent,
            gripper_working_height, n_cols, n_rows, to_first_anchor,
            anchor_spacing, position_correction=position_correction,
            calibration_approach_from=calibration_approach_from)

        self.z0_working_height = 45.0

        # TODO use self.full for vial presence or whether vial has been filled
        # or what?
        # support less than full box? support different amounts in some?
        # separate state variables for vial presence and fill status?


    def get(self, xy, ij):
        """
        """
        # TODO rename latter to z2_.. in maple
        zw = self.robot.z2_to_worksurface - self.flymanip_working_height
        if self.robot is not None:
            self.robot.moveXY(xy)
            self.robot.moveZ2(zw)

        grip_vial(self.robot)

        zt = self.robot.z2_to_worksurface - self.extent[2]
        if self.robot is not None:
            self.robot.moveZ2(zt)


    def put(self, xy, ij):
        """
        """
        zw = self.robot.z2_to_worksurface - self.flymanip_working_height
        if self.robot is not None:
            self.robot.moveXY(xy)
            self.robot.moveZ2(zw)

        release_vial(self.robot)

        zt = self.robot.z2_to_worksurface - self.extent[2]
        if self.robot is not None:
            self.robot.moveZ2(zt)


# TODO maybe inherit maple.module?
class Scale:
    def __init__(self, robot, offset, port='/dev/ttyACM0'):
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

       
robot = maple.robotutil.MAPLE(os.path.join(maple.__path__[0], 'MAPLE.cfg'))
# TODO 
offset = (50, 50)
vialbox = ScintillationVialBox(robot, offset)
scale = Scale()

# (empty of empty vials)
while not vialbox.is_empty():
    vialbox.get_next()

    

    # 2-list w/ float value and str repr of unit (e.g. 'g')
    # None if weight is not stable.
    #print(scale.scale.get_weight_stable())

