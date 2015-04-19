# Keithley_2000.py driver for Keithley 2000 DMM
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <qtlab@mcschaafsma.nl>, 2008
# Reinier Heeres <reinier@heeres.eu>, 2008 - 2010
#
# Update december 2009:
# Michiel Jol <jelle@michieljol.nl>
#
# Update and cleanup 2015: 
# Attila Geresdi
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from instrument import Instrument
import visa
import types
import logging
import numpy

import qt

def bool_to_str(val):
    '''
    Function to convert boolean to 'ON' or 'OFF'
    '''
    if val == True:
        return "ON"
    else:
        return "OFF"

class Keithley_2000(Instrument):
    '''
    This is the driver for the Keithley 2000 Multimeter

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'Keithley_2000',
        address='<GBIP address>',
        reset=<bool>,
        change_display=<bool>,
        change_autozero=<bool>)
    '''

    def __init__(self, name, address, reset=False,
            change_display=True, change_autozero=True, set_defaults=False):
        '''
        Initializes the Keithley_2000, and communicates with the wrapper.

        Input:
            name (string)           : name of the instrument
            address (string)        : GPIB address
            reset (bool)            : resets to default values
            change_display (bool)   : If True (default), automatically turn off
                                        display during measurements.
            change_autozero (bool)  : If True (default), automatically turn off
                                        autozero during measurements.
            set_defaults (bool)     : If True, sets the default settings defined in the driver
        Output:
            None
        '''
        # Initialize wrapper functions
        logging.info('Initializing instrument Keithley_2000')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._address = address
        self._visainstrument = visa.instrument(self._address)
        self._change_display = change_display
        self._change_autozero = change_autozero

        # Add parameters to wrapper
        self.add_parameter('range',
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            minval=0.0, maxval=1000, type=types.FloatType)
        self.add_parameter('trigger_continuous',
            flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)
        self.add_parameter('trigger_count',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)
        self.add_parameter('trigger_delay',
            flags=Instrument.FLAG_GETSET,
            units='s', minval=0, maxval=999999.999, type=types.FloatType)
        self.add_parameter('trigger_source',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType, format_map={
                            0: "Immediate",
                            1: "External",
                            2: "Timer",
                            3: "Manual",
                            4: "Bus"})
        self.add_parameter('trigger_timer',
            flags=Instrument.FLAG_GETSET,
            units='s', minval=0.001, maxval=999999.999, type=types.FloatType)
        self.add_parameter('mode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType, format_map={
                            0: 'AC Current',
                            1: 'DC Current',
                            2: 'AC Voltage',
                            3: 'DC Voltage',
                            4: '2W Resistance',
                            5: '4W Resistance',
                            6: 'Period',
                            7: 'Frequency',
                            8: 'Temperature',
                            9: 'Diode',
                            10: 'Continuity'})
        self.add_parameter('digits',
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            minval=4, maxval=7, type=types.IntType)
        self.add_parameter('readlastval', flags=Instrument.FLAG_GET,
            units='AU',
            type=types.FloatType,
            tags=['measure'])
        self.add_parameter('readnextval', flags=Instrument.FLAG_GET,
            units='AU',
            type=types.FloatType,
            tags=['measure'])
        self.add_parameter('integration_time',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType, minval=0.01, maxval=10, units='PLC')
        self.add_parameter('display', flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)
        self.add_parameter('autozero', flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)
        self.add_parameter('averaging', flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)
        self.add_parameter('averaging_count',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType, minval=1, maxval=100)
        self.add_parameter('averaging_type',
            flags=Instrument.FLAG_GETSET,
            type=types.BooleanType, format_map={False:'Repeating', True:'Moving'})
        self.add_parameter('autorange',
            flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)
        self.add_parameter('status_measurement',
            flags=Instrument.FLAG_GET,
            type=types.IntType)
        self.add_parameter('status_operation',
            flags=Instrument.FLAG_GET,
            type=types.IntType)        

        # Connect to measurement flow to detect start and stop of measurement
        qt.flow.connect('measurement-start', self._measurement_start_cb)
        qt.flow.connect('measurement-end', self._measurement_end_cb)

        if reset:
            self.reset()
        else:
            self.get_all()
            if set_defaults:
                self.set_defaults()

# --------------------------------------
#           functions
# --------------------------------------

    def get_all(self):
        '''
        Reads all relevant parameters from instrument

        Input:
            None

        Output:
            None
        '''
        logging.info('Get all relevant data from device')
        self.get_mode()
        self.get_range()
        self.get_trigger_continuous()
        self.get_trigger_count()
        self.get_trigger_delay()
        self.get_trigger_source()
        self.get_trigger_timer()
        self.get_mode()
        self.get_digits()
        self.get_integration_time()
        self.get_display()
        self.get_autozero()
        self.get_averaging()
        self.get_averaging_count()
        self.get_averaging_type()
        self.get_autorange()
        self.get_readlastval()

    def reset(self):
        '''
        Resets instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.debug('Resetting instrument')
        self._visainstrument.write('*RST')
        self.get_all()

    def set_defaults(self):
        '''
        Set to driver defaults:
        Output=data only
        Mode=Volt:DC
        Digits=7
        Trigger=Continuous
        Range=10 V
        NPLC=1
        Averaging=off
        '''

#        self._visainstrument.write('SYST:PRES')
#        self._visainstrument.write(':FORM:ELEM READ')
            # Sets the format to only the read out, all options are:
            # READing = DMM reading, UNITs = Units,
            # TSTamp = Timestamp, RNUMber = Reading number,
            # CHANnel = Channel number, LIMits = Limits reading

        self.set_mode(4)
        self.set_digits(7)
        self.set_trigger_continuous(True)
        self.set_range(10)
        self.set_nplc(1)
        self.set_averaging(False)

# --------------------------------------
#           parameters
# --------------------------------------

    def do_get_readnextval(self):
        '''
        Waits for the next value available and returns it as a float.
.
        Note: if triggering was continuous before calling the function
        it has to be disabled to ensure that we get reading only upon the next trigger. 

        Input:
            None

        Output:
            value(float) : last triggered value on input
        '''
        if self.get_trigger_continuous():
            self.set_trigger_continuous(False)
            value=float(self._visainstrument.ask(':READ?'))
            self.set_trigger_continuous(True)
        else:
            value=float(self._visainstrument.ask(':READ?'))
        return value
        
    def do_get_readlastval(self):
        '''
        Returns the last measured value available and returns it as a float.
        Note that if this command is sent twice in one integration time it will
        return the same value.

        Example:
        If continually triggering at 1 PLC, don't use the command within 1 PLC
        again, but wait 20 ms. If you want the Keithley to wait for a new
        measurement, use get_readnextval.

        Input:
            None

        Output:
            value(float) : last triggered value on input
        '''
        logging.debug('Read last value')
        
        return float(self._visainstrument.ask('DATA?'))

#:<function>:RANG
#sets or queries the range of measurements
#this is only available for current, voltage and resistance measurements
#limits are changed according to function (see do_set_mode())
#GET_AFTER_SET ensures that the actual range is displayed

    def do_set_range(self, val):
        if self.get_mode() > 5:
            logging.error('Range cannot be specified for the current function')
            return False
        else:
            self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':RANG '+str(val))

    def do_get_range(self):
        if self.get_mode() > 5:
            logging.error('Range cannot be read for the current function')
            return False
        else:
            return float(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':RANG?'))

#:<function>:DIG
#sets or queries the number of digits to display
#this is not available for diode or continuity measurements
    def do_set_digits(self, val):
        if self.get_mode() > 8:
            logging.error('Cannot set the number of digits for the current function')
            return False
        else:
            self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':DIG '+str(val))

    def do_get_digits(self):
        if self.get_mode() > 8:
            logging.error('Cannot get the number of digits for the current function')
            return False
        else:        
            return int(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':DIG?'))

#:<function>:NPLC
#sets or queries integration time in number of power line cycles (NPLC)
#for everything except for period and frequency measurements
#:<function>:APER
#sets or queries the integration time in seconds for period or frequency measurements
    def do_set_integration_time(self, val):
        if self.get_mode() == 7 or self.get_mode() == 6:
            self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':APER '+str(val))
        else:
            self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':NPLC '+str(val))
    
    def do_get_integration_time(self):
        if self.get_mode() == 7 or self.get_mode() == 6:
            return float(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':APER?'))
        else:
            return float(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':NPLC?'))

#:TRIG:CONT
#sets or queries continuous triggering

    def do_set_trigger_continuous(self, val):
        if val:
            self._visainstrument.write(':INIT:CONT 1')
        else:
            self._visainstrument.write(':INIT:CONT 0')
            
    def do_get_trigger_continuous(self):
        return int(self._visainstrument.ask(':INIT:CONT?')) == 1

#:TRIG:COUN
#sets or queries the number of trigger events processed
#For infinite (INF), set zero
    def do_set_trigger_count(self, val):
        if val == 0:
            self._visainstrument.write(':TRIG:COUN INF')
        else:
            self._visainstrument.write(':TRIG:COUN '+str(val))

    def do_get_trigger_count(self):
        temp=self._visainstrument.ask(':TRIG:COUN?').strip()
        if temp == '+9.9e37':
            return 0
        else:
            return int(temp)
        
#:TRIG:DEL
#sets or queries trigger delay

    def do_set_trigger_delay(self, val):
        self._visainstrument.write(':TRIG:DEL '+ str(val))

    def do_get_trigger_delay(self):
        return float(self._visainstrument.ask(':TRIG:DEL?'))

#:TRIG:SOUR
#queries or sets the trigger source
    def do_set_trigger_source(self, val):
        if val == 0:
            self._visainstrument.write(':TRIG:SOUR IMM')
        elif val == 1:
            self._visainstrument.write(':TRIG:SOUR EXT')
        elif val == 2:
            self._visainstrument.write(':TRIG:SOUR TIM')
        elif val == 3:
            self._visainstrument.write(':TRIG:SOUR MAN')
        elif val == 4:
            self._visainstrument.write(':TRIG:SOUR BUS')
        else:
            logging.error('Invalid trigger source')
        
    def do_get_trigger_source(self):
        temp = self._visainstrument.ask(':TRIG:SOUR?').strip()
        if temp == 'IMM':
            return 0
        elif temp == 'EXT':
            return 1
        elif temp == 'TIM':
            return 2
        elif temp == 'MAN':
            return 3
        elif temp == 'BUS':
            return 4
        else:
            return None

#:TRIG:TIM
#sets or queries trigger timer effective for TIM trigger source
    def do_set_trigger_timer(self, val):
        self._visainstrument.write(':TRIG:TIM '+str(val))

    def do_get_trigger_timer(self):
        return float(self._visainstrument.ask(':TRIG:TIM?'))

#:TRIG:INIT
#initiate triggering
    def trigger_init(self):
        self._visainstrument.write(':INIT')

#:TRIG:ABOR
#abort triggering, puts the instrument into the idle state
    def trigger_abort(self):
        self._visainstrument.write(':ABOR')

#:FUNC
#Sets or queries the measured function
#GET_AFTER_SET ensures that related parameters e.g. range are read
#upon changing it
    def do_set_mode(self, val):
        if val == 0:
            self._visainstrument.write(':FUNC "CURR:AC"')
            self.set_parameter_options('readlastval', units='A')
            self.set_parameter_options('readnextval', units='A')
            self.set_parameter_options('range', maxval=3.1)
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 1:
            self._visainstrument.write(':FUNC "CURR:DC"')
            self.set_parameter_options('readlastval', units='A')
            self.set_parameter_options('readnextval', units='A')
            self.set_parameter_options('range', maxval=3.1)
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 2:
            self._visainstrument.write(':FUNC "VOLT:AC"')     
            self.set_parameter_options('readlastval', units='V')
            self.set_parameter_options('readnextval', units='V')
            self.set_parameter_options('range', maxval=1010)
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 3:
            self._visainstrument.write(':FUNC "VOLT:DC"')
            self.set_parameter_options('readlastval', units='V')
            self.set_parameter_options('readnextval', units='V')
            self.set_parameter_options('range', maxval=1010)
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 4:
            self._visainstrument.write(':FUNC "RES"')
            self.set_parameter_options('readlastval', units='Ohm')
            self.set_parameter_options('readnextval', units='Ohm')
            self.set_parameter_options('range', maxval=120e6)
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 5:
            self._visainstrument.write(':FUNC "FRES"')
            self.set_parameter_options('readlastval', units='Ohm')
            self.set_parameter_options('readnextval', units='Ohm')
            self.set_parameter_options('range', maxval=120e6)
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 6:
            self._visainstrument.write(':FUNC "PER"')
            self.set_parameter_options('readlastval', units='s')
            self.set_parameter_options('readnextval', units='s')
            self.set_parameter_options('integration_time', units='s')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 7:
            self._visainstrument.write(':FUNC "FREQ"')
            self.set_parameter_options('readlastval', units='Hz')
            self.set_parameter_options('readnextval', units='Hz')
            self.set_parameter_options('integration_time', units='s')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 8:
            self._visainstrument.write(':FUNC "TEMP"')
            self.set_parameter_options('readlastval', units='K')
            self.set_parameter_options('readnextval', units='K')
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GETSET)
        elif val == 9:
            self._visainstrument.write(':FUNC "DIOD"')
            self.set_parameter_options('readlastval', units='V')
            self.set_parameter_options('readnextval', units='V')
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GET)
        elif val == 10:
            self._visainstrument.write(':FUNC "CONT"')
            self.set_parameter_options('readlastval', units='')
            self.set_parameter_options('readnextval', units='')
            self.set_parameter_options('integration_time', units='PLC')
            self.set_parameter_options('integration_time', minval=0.01)
            self.set_parameter_options('integration_time', maxval=10.0)
            self.set_parameter_options('integration_time', flags=Instrument.FLAG_GET)           
        else:
            logging.error('Tried to set invalid mode')
        self.get_all()
                
    def do_get_mode(self):
        temp = self._visainstrument.ask(':FUNC?').strip().strip('"')
        if temp == 'CURR:AC':
            return 0
        elif temp == 'CURR:DC':
            return 1
        elif temp == 'VOLT:AC':
            return 2
        elif temp == 'VOLT:DC':
            return 3
        elif temp == 'RES':
            return 4
        elif temp == 'FRES':
            return 5
        elif temp == 'PER':
            return 6
        elif temp == 'FREQ':
            return 7
        elif temp == 'TEMP':
            return 8
        elif temp == 'DIOD':
            return 9
        elif temp == 'CONT':
            return 10

#DISP:ENAB
#turns the display on or off (might help with some noise pickup)
    def do_set_display(self, val):
        if val:
            self._visainstrument.write('DISP:ENAB 1')
        else:
            self._visainstrument.write('DISP:ENAB 0')

    def do_get_display(self):
        return int(self._visainstrument.ask('DISP:ENAB?')) == 1

#:AZER:STAT
#sets or queries autozero. If ON, better accuracy is achieved 
#at the expense of speed.
#TODO: ensure that instrument is in IDLE state before setting autozero
    def do_set_autozero(self, val):
        if val:
            self._visainstrument.write(':SYST:AZER:STAT 1')
        else:
            self._visainstrument.write(':SYST:AZER:STAT 0')

    def do_get_autozero(self):
        return int(self._visainstrument.ask(':SYST:AZER:STAT?')) == 1
    
#:<function>:AVER:STAT
#sets or queries averaging.
#Note: this is only available for current, voltage, resistance and temperature
    def do_set_averaging(self, val):
        if self.get_mode() == 10 or self.get_mode() == 9 or self.get_mode() == 7 or self.get_mode() == 6:
            logging.error('Cannot set averaging for the current function')
            return False
        else:       
            if val:
                self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':AVER:STAT 1')
            else:
                self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':AVER:STAT 0')
               
    def do_get_averaging(self):
        if self.get_mode() == 10 or self.get_mode() == 9 or self.get_mode() == 7 or self.get_mode() == 6:
            logging.error('Cannot get averaging for the current function')
            return False        
        else:
            return int(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':AVER:STAT?')) == 1

#:<function>:AVER:COUN
#sets or queries averaging count.
#Note: this is only available for current, voltage, resistance and temperature
    def do_set_averaging_count(self, val):
        if self.get_mode() == 10 or self.get_mode() == 9 or self.get_mode() == 7 or self.get_mode() == 6:
            logging.error('Cannot set averaging count for the current function')
            return False
        else:
            self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':AVER:COUN '+str(val))
            
    def do_get_averaging_count(self):
        if self.get_mode() == 10 or self.get_mode() == 9 or self.get_mode() == 7 or self.get_mode() == 6:
            logging.error('Cannot get averaging count for the current function')
            return False
        else:
            return int(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':AVER:COUN?'))

#:<function>:AVER:TCON
#sets or queries averaging type (moving or repeating).
#Note: this is only available for current, voltage, resistance and temperature
    def do_set_averaging_type(self, val):
        if self.get_mode() == 10  or self.get_mode() == 9 or self.get_mode() == 7 or self.get_mode() == 6:
            logging.error('Cannot set averaging type for the current function')
            return False
        else:
            if val:
                self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':AVER:TCON MOV')
            else:
                self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':AVER:TCON REP')

    def do_get_averaging_type(self):
        if self.get_mode() == 10 or self.get_mode() == 9 or self.get_mode() == 7 or self.get_mode() == 6:
            logging.error('Cannot get averaging type for the current function')
            return False
        else:
            return self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':AVER:TCON?').strip() == 'MOV'

##:<function>:RANG:AUTO
#sets or queries averaging type (moving or repeating).
#Note: this is only available for current, voltage and resistance
    def do_set_autorange(self, val):
        if self.get_mode() > 5:
            logging.error('Cannot set autorange for the current function')
            return False
        else:
            if val:
                self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':RANG:AUTO 1')
            else:
                self._visainstrument.write(':'+self._int_to_function(self.get_mode())+':RANG:AUTO 0')            

    def do_get_autorange(self):
        if self.get_mode() > 5:
            logging.error('Cannot get autorange for the current function')
            return False
        else:
            return int(self._visainstrument.ask(':'+self._int_to_function(self.get_mode())+':RANG:AUTO?')) == 1

#:STAT:MEAS?
#reads measurement event register
#note that reading the register clears it
    def do_get_status_measurement(self):
        return int(self._visainstrument.ask(':STAT:MEAS?'))

#:STAT:OPER?
#reads measurement event register
#note that reading the register clears it
    def do_get_status_operation(self):
        return int(self._visainstrument.ask(':STAT:OPER?'))
    
# --------------------------------------
#           Internal Routines
# --------------------------------------

    def _int_to_function(self, val):
        if val == 0:
            return 'CURR:AC'
        elif val == 1:
            return 'CURR:DC'
        elif val == 2:
            return 'VOLT:AC'
        elif val == 3:
            return 'VOLT:DC'
        elif val == 4:
            return 'RES'
        elif val == 5:
            return 'FRES'
        elif val == 6:
            return 'PER'
        elif val == 7:
            return 'FREQ'
        elif val == 8:
            return 'TEMP'
        elif val == 9:
            return 'DIOD'
        elif val == 10:
            return 'CONT'
        else:
            return None

    def _measurement_start_cb(self, sender):
        '''
        Things to do at starting of measurement
        '''
        if self._change_display:
            self.set_display(False)
            #Switch off display to get stable timing
        if self._change_autozero:
            self.set_autozero(False)
            #Switch off autozero to speed up measurement

    def _measurement_end_cb(self, sender):
        '''
        Things to do after the measurement
        '''
        if self._change_display:
            self.set_display(True)
        if self._change_autozero:
            self.set_autozero(True)

