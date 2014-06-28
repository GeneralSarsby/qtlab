# rigol_dg.py driver for Rigol DG4000 waveform generators.
# Supported devices:
#    -- DG 4062
#    -- DG 4102
#    -- DG 4162
# 
# Attila Geresdi (attila.geresdi@gmail.com) 2014
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
import string

import qt

class rigol_dg4000(Instrument):
    '''
    This is the driver for the Rigol DG4000 series waveform generator
    For list of supported devices, refer to the header of this file
    '''
    
    def __init__(self, name, type, address):
        
        logging.info("Initializing instrument Rigol " + type + " on address " + str(address))
        Instrument.__init__(self, name, tags=['physical'])
        
        #Pass init parameters to global constants

        self._type=type
        self._address=address
        self._visainstrument=visa.instrument(self._address, term_chars='\n')
        
        #create underlying instances of one counter and two output channels
        
        qt.instruments.create(name + '_counter', 'rigol_dg_counter', type=self._type, phy=self._visainstrument, channel=1)
        qt.instruments.create(name + '_CH1', 'rigol_dg_wavegen', type=self._type, phy=self._visainstrument, channel=1)
        qt.instruments.create(name + '_CH2', 'rigol_dg_wavegen', type=self._type, phy=self._visainstrument, channel=2)
        
        #Add parameters common for all instruments
        
        #System parameters
        
        self.add_parameter('beeper', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'off',True:'on'})
        
        self.add_parameter('error', type=types.StringType,
                flags=Instrument.FLAG_GET)

        self.add_parameter('keyboard_lock', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'off',True:'on'})
        
        self.add_parameter('sync_10MHz',type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'Internal', True:'External'})
        
        self.add_parameter('display_brightness', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='%',
                           minval=0.0, maxval=100.0, format='%.2f')
        
        self.add_parameter('screensaver', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'disabled',True:'enabled'})
        
        self.get_all()
    
#Common functions
           
    #Reads all available parameters
    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)
    
    
#SYSTEM instructions
    
    #SYST:BEEP
    #sets or queries the beeper for button press
    def do_get_beeper(self):
        return self._visainstrument.ask(":SYST:BEEP:STAT?\n").strip() == "ON"
    
    def do_set_beeper(self, value):
        if value:
            self._visainstrument.write(":SYST:BEEP:STAT ON\n")
        else:
            self._visainstrument.write(":SYST:BEEP:STAT OFF\n")
        self.get_error()
    
    #SYST:BEEP
    #beeps once
    def beep(self):
        if self.get_beeper:
            self._visainstrument.write(":SYST:BEEP\n")
        else:
            logging.error(__name__ + ": Beeper disabled")
        self.get_error()
    
    #SYST:ERRcounter
    #reads the error string
    def do_get_error(self):
        return self._visainstrument.ask(":SYST:ERR?\n")
    
    #SYST:RESTART
    #restarts instrument
    def restart(self):
        self._visainstrument.write(":SYST:RESTART\n")
    
    #SYST:SHUTDOWN
    #shuts down instrument
    def shutdown(self):
        self._visainstrument.write(":SYST:SHUTDOWN\n")
        
    #SYST:KLOC
    #sets or queries front panel keyboard lock
    def do_get_keyboard_lock(self):
        return self._visainstrument.ask(":SYST:KLOC?\n").strip() == "ON"
    
    def do_set_keyboard_lock(self, value):
        if value:
            self._visainstrument.write(":SYST:KLOC ON\n")
        else:    
            self._visainstrument.write(":SYST:KLOC OFF\n")
        self.get_error()
            
    #SYST:CSC
    #copies channel configuration including output settings, modulation, freq, amplitude, burst
    def copy_settings_ch1_to_ch2(self):
        self._visainstrument.write(":SYST:CSC CH1,CH2\n")
        self.get_error()
    
    def copy_settings_ch2_to_ch1(self):
        self._visainstrument.write(":SYST:CSC CH2,CH1\n")
        self.get_error()
        
    #SYST:CWC
    #copies arbitrary waveform between channels. Only available in arb. mode!
    def copy_waveform_ch1_to_ch2(self):
        self._visainstrument.write(":SYST:CWC CH1,CH2\n")
        self.get_error()
    
    def copy_waveform_ch2_to_ch1(self):
        self._visainstrument.write(":SYST:CWC CH2,CH1\n")
        self.get_error()    
    
    #SYST:ROSC:SOUR
    #sets or queries the 10MHz ref. source: internal or external
    def do_get_sync_10MHz(self):
        return self._visainstrument.ask(":SYST:ROSC:SOUR?\n").strip() == "EXT"
    
    def do_set_sync_10MHz(self, value):
        if value:
            self._visainstrument.write("SYST:ROSC:SOUR EXT\n")
        else:
            self._visainstrument.write("SYST:ROSC:SOUR INT\n")
        self.get_error()        

#Display instructions

    #DISP:BRIG
    #sets or queries the display brightness
    def do_get_display_brightness(self):
        return float(self._visainstrument.ask(":DISP:BRIG?\n").strip('%'))
    
    def do_set_display_brightness(self, value):
        self._visainstrument.write(":DISP:BRIG"+str(value)+"\n")
        self.get_error()
    
    #DISP:SAV
    #queries or enables/disables the screensaver function
    def do_get_screensaver(self):
        return self._visainstrument.ask(":DISP:SAV?\n").strip() == "ON"
    
    def do_set_screensaver(self, value):
        if value:
            self._visainstrument.write(":DISP:SAV ON\n")
        else:
            self._visainstrument.write(":DISP:SAV OFF\n")
        self.get_error()
    
    #DISP:SAV:IMM
    #puts the instrument into screensaver mode immediately
    def screensaver_on(self):
        self._visainstrument.write(":DISP:SAV:IMM\n")
        
# Common SCPI instructions

    #*RST
    #returns instrument to factory default settings
    def reset(self):
        self._visainstrument.write("*RST\n")
    
    #*TRG
    #triggers output
    def trigger(self):
        self._visainstrument.write("*TRG\n")

    