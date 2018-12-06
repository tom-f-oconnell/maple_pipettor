#!/usr/bin/env python3

"""
Script to use MAPLE, with a scale and some purpose-built effectors, to aliquot
out liquids by mass with a serological pipette.
"""

from __future__ import print_function
from __future__ import division

#import maple
#import maple.robotutil
from mettler_toledo_device import MettlerToledoDevice

scale = MettlerToledoDevice(port='/dev/ttyACM0')
print(scale.get_balance_data())

while True:
    # 2-list w/ float value and str repr of unit (e.g. 'g')
    # None if weight is not stable.
    print(scale.get_weight_stable())
