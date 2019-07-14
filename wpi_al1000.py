#!/usr/bin/env python3

"""
This module implements a driver for the AL1000 syringe pump from World Precision
Instruments.

(adapted from github.com/CINF/PyExpLabSys/blob/1412979/PyExpLabSys/drivers,
 which is distributed under the GPLv3 license)
"""

import time

import serial
import crc16


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
        reply_unicode = reply.decode("ascii")
        return reply_unicode[4:-1]

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

    def set_diam(self, diameter):
        """Sets the syringe diameter in mm

        From the manual:
        Setting the syringe diameter also sets the units for “Volume to be
        Dispensed” and “Volume Dispensed”
        """
        # TODO need to handle other things this changes (as docstring)?
        # TODO limit precision?
        # TODO TODO can this take a unit string suffix as w/ rate?
        return self._send_command('DIA{}'.format(diameter))

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
        # TODO is False an appropriate default here? what's it mean?
        # is it not just selecting one of the other units?
        # should this even be supported?
        if unit == False:
            self._send_command("FUNRAT")
            return self._send_command("RAT" + str(num))
        else:
            self._send_command("FUNRAT")
            return self._send_command("RAT" + str(num) + unit)

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
        return self._send_command("VOL" + str(num))

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


    def dispense(self, ml):
        """Dispenses volume in mL
        """
        # TODO retract pump first / detect when syringe needs to be changed /
        # motor is stalled?
        # TODO TODO is stall detection even working on our pump?
        r1 = self.set_direction('INF')
        # TODO is this actually ml?
        r2 = self.set_vol(ml)
        # TODO need to clear current dispensed vol?

        r3 = self.start_program()


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
    import ipdb; ipdb.set_trace()
    # This should disable safe mode if necessary
    # may need to call a few times sequentially if there is a short timeout (?)
    # do right after powerup
    #ret = pump._send_command("\x02\x08SAF0\x55\x43\x03")


if __name__ == "__main__" :
    main()

