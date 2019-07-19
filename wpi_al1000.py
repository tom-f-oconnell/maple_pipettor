#!/usr/bin/env python3

"""
This module implements a driver for the AL1000 syringe pump from World Precision
Instruments.

(adapted from github.com/CINF/PyExpLabSys/blob/1412979/PyExpLabSys/drivers,
 which is distributed under the GPLv3 license)
"""

from __future__ import print_function

import sys
import time
import warnings

import serial
import crc16


def _format_float(num):
    """Returns str w/ float formatted as per the manual.
    From the manual:
    'Maximum of 4 digits plus 1 decimal point. Maximum of 3 digits to the
    right of the decimal point'
    """
    if num >= 10000:
        raise ValueError('floats sent to AL-1000 can only have 4 digits')
    # TODO it doesn't err if there is nothing to right of decimal point,
    # does it? test
    return '{:.3f}'.format(num)[:5]


class AL1000(object):
    """Driver for the AL1000 syringe pump"""
    
    def __init__(self, port="/dev/ttyUSB0", baudrate=19200):
        # TODO does this need to be changed for safe mode?
        self.serial = serial.Serial(
            port=port, baudrate=baudrate, timeout=1,
            parity=serial.PARITY_NONE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            
        )
        self.safe_mode = False

        self.capacity = None
        self.max_rate = None
        self.min_rate = None

    def _send_command(self, command):
        # TODO switch all communication to safe mode protocol once i get that
        # working
        '''
        encoded_cmd = command.encode('ascii')
        # TODO how did octopus get away w/ {:s} for crc? it is bytes type for
        # me and that fails w/ non-empty format str
        length = '{:c}'.format(len(encoded_cmd) + 4).encode('ascii')
        crc = crc16.crc16xmodem(encoded_cmd)
        encoded_crc = crc.to_bytes(2, byteorder='big')
        # TODO do we actually wand b'\x03' suffix? octopus doesn't seem to
        to_send = length + encoded_cmd + encoded_crc # + b'\x03'
        # TODO delete
        print('sending:', to_send)
        #
        self.serial.write(to_send)
        time.sleep(0.5)
        # TODO need both of these calls? won't read by itself read
        # everything in waiting?
        waiting = self.serial.inWaiting()
        reply = self.serial.read(waiting)

        print('length of reply:', waiting)
        print('reply:', reply)

        # FIXME implement crc16 checksum check
        # TODO copy from octopus repo
        
        # TODO need to at least discard crc data to have replies be the
        # same?

        # this should be the firmware version: NE1000V3.928
        import ipdb; ipdb.set_trace()

        ret = reply.decode('ascii')

        # TODO TODO TODO are replies to safe mode commands in diff format?
        return ret[4:-1]
        '''
        formatted_command = command + "\r"
        self.serial.write(formatted_command.encode("ascii"))
        time.sleep(0.5)
        waiting = self.serial.inWaiting()
        reply = self.serial.read(waiting)
        try:
            reply_unicode = reply.decode("ascii")
            return reply_unicode[4:-1]
        except UnicodeDecodeError as err:
            print('command:', command)
            print('reply:', reply)
            raise

    def get_firmware(self):
        """Returns the str firmware version
        """
        # TODO on first run one time, '?R' was returned,
        # but after that, 'NE1000V3.928' was... wait untli ?R isn't returned?
        # what does that code mean?
        return self._send_command("VER")

    def get_diam(self):
        """Returns the syringe diameter in mm
        """
        return float(self._send_command('DIA'))

    def set_diam(self, diameter, warn=True):
        """Sets the syringe diameter in mm

        From the manual:
        Setting the syringe diameter also sets the units for 'Volume to be
        Dispensed' and 'Volume Dispensed'
        """
        if warn:
            warnings.warn('use set_syringe to get rate bounds checking')

        # TODO need to handle other things this changes (as docstring)?
        # TODO limit precision?
        # TODO TODO can this take a unit string suffix as w/ rate?
        return self._send_command('DIA' + _format_float(diameter))

    def get_rate(self):
        """Returns the pump rate in mL/min
        """
        ret = self._send_command("RAT")
        rate = float(ret[:-2])
        vol_unit_char = ret[-2]
        time_unit_char = ret[-1]
        if vol_unit_char == 'U':
            rate = rate / 1000.0
        elif vol_unit_char != 'M':
            raise ValueError('unexpected volume unit code: {}'.format(
                vol_unit_char))

        if time_unit_char == 'H':
            rate = rate / 60.0
        elif time_unit_char != 'M':
            raise ValueError('unexpected time unit code: {}'.format(
                time_unit_char))

        return rate

    # TODO does this automatically get limited by current diam according to
    # table in manual? or should i implement that here? err if outside range?
    def set_rate(self, num, unit=False):
        # TODO is 34.38 actually as high as it goes? if so, raise appropriate
        # error code here
        """Sets the pump rate.
        
        Args:
            num (float): The flow rate (0 mL/min - 34.38 mL/min)
            unit (str): For valid values see below.
        
        Valid units are:
        UM=microL/min
        MM=milliL/min 
        UH=microL/hr 
        MH=milliL/hour
        """
        if self.max_rate is None:
            warnings.warn('use set_syringe before set_rate to get rate ' +
                'bounds checking')
        else:
            # TODO include my ~viscosity state var in check here too
            if num > self.max_rate:
                raise ValueError('rate > maximum for this syringe')

            if num < self.min_rate:
                raise ValueError('rate < minimum for this syringe')

        # TODO is False an appropriate default here? what's it mean?
        # is it not just selecting one of the other units?
        # should this even be supported?
        if unit == False:
            self._send_command("FUNRAT")
            return self._send_command("RAT" + _format_float(num))
        else:
            self._send_command("FUNRAT")
            return self._send_command("RAT" + _format_float(num) + unit)

    # TODO rename to get/set_target_vol?
    def get_vol(self):
        """Gets target volume in mL
        """
        ret = self._send_command('VOL')
        vol = float(ret[:-2])
        # factor into a general unit conversion fn?
        unit = ret[-2:]
        if unit == 'UL':
            vol = vol / 1000.0
        elif unit != 'ML':
            raise ValueError('unexpected volume unit: {}'.format(unit))
        return vol

    def set_vol(self, num):
        # TODO TODO what exactly does this docstring mean?
        # TODO will it pump only after start_program? will this apply to that,
        # if no "phase" param given?
        """Sets the pumped volume to the pump. The pump will pump until the given volume has been dispensed.
        
        Args:
            num (float): The volume to de dispensed (no limits)
            
        """
        # TODO need to limit precision of float w/ str formatting?
        # TODO accept unit string suffix? implement
        return self._send_command("VOL" + _format_float(num))

    def get_vol_disp(self):
        """Returns the dispensed volume since last reset.
        """
        return self._send_command("DIS")
    
    def clear_vol_disp(self, direction = "both"):
        """Clear pumped volume for one or more dircetions. 
        
        Args:
            direction (string): The pumping direction. Valid directions are: INF=inflation, WDR=withdrawn, both=both directions. Default is both
        
        """
        if direction == "INF":
            return self._send_command("CLDINF")
        if direction == "WDR":
            return self._send_command("CLDWDR")
        if direction == "both":
            return self._send_command("CLDINF")
            return self._send_command("CLDWDR")
    
    # TODO what are valid values for "phase"? whats the point?
    def set_fun(self, phase):
        """Sets the program function
        """
        return self._send_command("FUN" + phase)

    def set_safe_mode(self, num):
        """Enables or disables safe mode.
        
        Args:
            If num=0 --> Safe mode disables
                If num>0 --> Safe mode enables with the requirement that valid communication must be received every num seconds
        """
        if not type(num) is int or num < 0 or num > 255:
            # Not explicitly in manual, but it doesn't list it as a float, and
            # range is 0-255, so it seems likely.
            raise ValueError('timeout seconds must be an integer in [0,255]')

        # TODO do this after message, so if in safe mode currently, message can
        # still be sent
        if num == 0:
            self.safe_mode = False
        else:
            self.safe_mode = True
        return self._send_command("SAF" + str(num))

    def start_program(self):
        return self._send_command("RUN")

    def stop_program(self):
        return self._send_command("STP")

    def get_direction(self):
        """Returns the curret pumping direction"""
        return self._send_command("DIR")

    def set_direction(self, direction):
        """Sets the pumping direction
        
        Args:
            directoin=INF --> Pumping dirction set to infuse
                directoin=WDR --> Pumping dirction set to Withdraw
                    directoin=REV --> Pumping dirction set to the reverse current pumping direction
        """
        if direction == "INF":
            return self._send_command("DIRINF")
        if direction == "WDR":
            return self._send_command("DIRWDR")
        if direction == "REV":
            return self._send_command("DIRREV")

    def retract_pump(self):
        # TODO TODO what does "remember to stop manually" mean?  need to
        # instruct the pump to stop if it detects motor stall or will it do that
        # automatically? implement s.t. software limits are maintained and
        # respected?
        """Fully retracts the pump. REMEMBER TO STOP MANUALLY!
        """
        self.set_direction("WDR")
        self.set_vol(9999)
        self.set_rate(34.38, "MM")
        self.start_program()


    def can_dispense(self, ml):
        """Returns whether the syringe should have enough volume left to
        dispense the requested amount.
        """
        if self.capacity is None:
            raise RuntimeError('set pump.capacity or call set_syringe first')

        # TODO maybe provide some way to input actual current volume in
        # syringe in case things need restarted (prompt w/ default assuming
        # syringe is full?)

        # Note that this seems to reset across serial sessions even if the
        # pump maintains power, so it's only accurate if the syringe started
        # completely full.
        vd_str = self.get_vol_disp()
        # Ignoring the "withdraw" part of the returned state
        volume_dispensed = float(vd_str[1:6])
        unit = vd_str[-2:]
        if unit == 'UL':
            volume_dispensed = volume_dispensed / 1000.0

        # TODO need some buffer to avoid crashing in to the very end of the
        # syringe if it isn't totally fully (or even if it is?)?
        if volume_dispensed + ml >= self.capacity:
            return False
        return True


    def dispense(self, ml, block=True):
        """Dispenses volume in mL.
        
        Returns False if syringe capacity is known and needs refilled capacity,
        True otherwise.
        """
        if block:
            # mL/min
            rate = self.get_rate()
            time_sec = (ml / rate) * 60.0

        # TODO retract pump first / detect when syringe needs to be changed /
        # motor is stalled?
        # TODO TODO is stall detection even working on our pump?
        r1 = self.set_direction('INF')
        # TODO is this actually ml?
        r2 = self.set_vol(ml)
        if self.capacity is not None:
            if not self.can_dispense(ml):
                return False

        self.start_program()
        # could subtract delay in start_program for communication?
        print('Waiting {:.1f} seconds for pump to finish... '.format(time_sec),
            end='')
        sys.stdout.flush()
        time.sleep(time_sec)
        print('done')
        return True


    def set_syringe(self, family='B-D', cc=60):
        """
        Taken from table in page 60 of AL-1000 manual.
        At least for BD, values measured w/ calipers seem pretty close
        (within about a percent at worst), and so are values reported in
        Harvard Apparatus Syringe Selection Guide.

        family: manufacturer / part series
        """
        # TODO conver to some pandas dataframe
        # As in Aladdin manual, max_rate units are ml/hr and
        # min_rate units are ul/hr
        # TODO convert all to ml/min before using
        # TODO probably some list_syringes fn or something
        syringes = {
            'B-D': {
                60: {
                    'diameter': 26.59,
                    # TODO determine whether these are appropriate for paraffin
                    # oil empirically. maybe some scalar to modify all max_rate
                    # by like something ~ viscosity?
                    'max_rate': 1699,
                    'min_rate': 23.35
                }
            },
            # mfg is HSW. diameter from www.restek.com/norm-ject-specs
            'NORM-JECT': {
                20: {
                    'diameter': 20.05,
                    # TODO determine these empirically
                    # taken from values for other 20mL syringes in WPI manual
                    'max_rate': 900,
                    'min_rate': 12
                }
            }
        }
        if family not in syringes or cc not in syringes[family]:
            raise ValueError('no data for this syringe. have:\n{}'.format(
                [(f, list(v.keys())) for f, v in syringes.items()]))
        
        # TODO use that pdf -> table stuff to read both pdfs in -> use whole
        # table?

        self.capacity = cc
        data = syringes[family][cc]
        # mL/hr -> mL/min
        self.max_rate = data['max_rate'] / 60.0
        # uL/hr -> mL/min
        self.min_rate = data['min_rate'] / (60 * 1000.0)
        diam = data['diameter']
        self.set_diam(diam, warn=False)
        print('Considering syringe ID to be {}mm'.format(diam))
        # TODO implement some kind of viscosity attribute which scales max rate
        # have that settable indep (0.5 is a hardcoded version of this now)
        rate = self.max_rate# * 0.2
        self.set_rate(rate, unit='MM')
        # To reflect actual sig figs on pump + verify correct setting.
        rate = self.get_rate()
        print('Using rate of {} mL/min'.format(rate))


def main():
    pump = AL1000()

    firmware = pump.get_firmware()
    print('firmware version:', firmware)
    diam = pump.get_diam()
    print(diam)
    rate = pump.get_rate()
    print(rate)
    vol = pump.get_vol()
    print(vol)
    vol_disp = pump.get_vol_disp()
    print(vol_disp)
    direction = pump.get_direction()
    print(direction)

    pump.set_syringe(family='B-D', cc=60)
    import ipdb; ipdb.set_trace()

    pump.dispense(5)
    import ipdb; ipdb.set_trace()
    # This should disable safe mode if necessary
    # may need to call a few times sequentially if there is a short timeout (?)
    # do right after powerup
    #ret = pump._send_command("\x02\x08SAF0\x55\x43\x03")


if __name__ == "__main__" :
    main()

