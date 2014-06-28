# rigol_dg_counter.py driver for Rigol DG series waveform generators.
# This driver defines the functions to handle the counter modul of the instrument.
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

class rigol_dg_counter(Instrument):
    '''
    This is the driver for the counter modul of the Rigol DG series waveform generators
    Usually this modul is invoked by the rigol_dgXXXX driver. 
    For list of supported devices, refer to those drivers.
    '''
    
    def __init__(self, name, type, phy, channel):
        
        logging.info("Initializing the counter modul of Rigol")
        Instrument.__init__(self, name, tags=['virtual'])
    
        #Pass init parameters to global constants

        self._type=type
        self._phy=phy
        self._ch=str(channel)   #Only here for future compatibility, not used yet
        
        self.add_parameter('enabled', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'disabled',True:'enabled'})

        self.add_parameter('attenuation', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'1X',True:'10X'})

        self.add_parameter('coupling', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'DC',True:'AC'})
        
        self.add_parameter('gatetime', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'Auto',1:'1 ms',2:'10 ms',3:'100 ms',4:'1 s',5:'10 s',6:'>10 s'})        
               
        self.add_parameter('hfreject', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'Disabled', True:'Enabled'})
        
        self.add_parameter('input_50_Ohm', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'1 MOhm', True:'50 Ohm'})

        self.add_parameter('trigger_level', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='V',
                           minval=-2.5, maxval=2.5, format='%.4f')
        
        self.add_parameter('sensitivity', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='%',
                           minval=0.0, maxval=100.0, format='%.2f')
        
        self.add_parameter('frequency', type=types.FloatType,
                           flags=Instrument.FLAG_GET,
                           units='Hz',
                           format='%.6f')

        self.add_parameter('period', type=types.FloatType,
                           flags=Instrument.FLAG_GET,
                           units='s',
                           format='%.6f')

        self.add_parameter('duty_cycle', type=types.FloatType,
                           flags=Instrument.FLAG_GET,
                           units='%',
                           format='%.6f')
        
        self.add_parameter('pos_width', type=types.FloatType,
                           flags=Instrument.FLAG_GET,
                           units='s',
                           format='%.6f')
                
        self.add_parameter('neg_width', type=types.FloatType,
                           flags=Instrument.FLAG_GET,
                           units='s',
                           format='%.6f')
        
        self.add_parameter('statistics', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'disabled',True:'enabled'})
        
        self.add_parameter('stats_display', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'digital',True:'curve'})               
        
        self.get_all()
        
#Common functions

    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)
    
#Device specific functions
    
    #COUN:STAT
    #queries, enables or disables the counter module
    def do_get_enabled(self):
        return self._phy.ask(":COUN?\n").strip() == "ON"
    
    def do_set_enabled(self,value):
        if value:
            self._phy.write(":COUN ON\n")
        else:
            self._phy.write(":COUNT OFF\n")

    #COUN:ATT
    #queries or sets the attenuation to 1X (False) or 10X (True)
    def do_get_attenuation(self):
        return self._phy.ask(":COUN:ATT?\n").strip() == "10X"
    
    def do_set_attenuation(self,value):
        if value:
            self._phy.write(":COUN:ATT 10X\n")
        else:
            self._phy.write(":COUN:ATT 1X\n")
    
    #COUN:COUP
    #queries or sets AC/DC (True/False) coupling of the counter input
    def do_get_coupling(self):
        return self._phy.ask(":COUN:COUP?\n").strip() == "AC"
    
    def do_set_coupling(self,value):
        if value:
            self._phy.write(":COUN:COUP AC\n")
        else:
            self._phy.write(":COUN:COUP DC\n")        
    
    #COUN:GATE
    #queries or sets the gatetime. For actual values refer to GUI
    def do_get_gatetime(self):
        temp=self._phy.ask(":COUN:GATE?").strip()
        if temp == "AUTO":
            return 0
        elif temp == "USER1":
            return 1
        elif temp == "USER2":
            return 2
        elif temp == "USER3":
            return 3
        elif temp == "USER4":
            return 4
        elif temp == "USER5":
            return 5
        elif temp == "USER6":
            return 6                
        else:
            return None
    
    def do_set_gatetime(self, value):
        if value == 0:
            self._phy.write(":COUN:GATE AUTO\n")
        else:
            self._phy.write(":COUN:GATE USER" + str(value) + "\n")
    
    #COUN:HF
    #queries or alters the high frequency reject of the input
    def do_get_hfreject(self):
        return self._phy.ask("COUN:HF?\n").strip() == "ON"
    
    def do_set_hfreject(self,value):
        if value:
            self._phy.write(":COUN:HF ON\n")
        else:
            self._phy.write(":COUN:HF OFF\n")
    
    #COUN:IMP
    #queries or sets the input impedance to 1 MOhm or 50 Ohm
    def do_get_input_50_Ohm(self):
        return self._phy.ask(":COUN:IMP?\n").strip() == "50"
    
    def do_set_input_50_Ohm(self,value):
        if value:
            self._phy.write(":COUN:IMP 50\n")
        else:
            self._phy.write(":COUN:IMP 1M\n")
                     
    #COUN:LEVE
    #queries or sets the trigger level
    def do_get_trigger_level(self):
        return float(self._phy.ask(":COUN:LEVE?\n"))
    
    def do_set_trigger_level(self,value):
        self._phy.write(":COUN:LEVE " + str(value) +"\n")
        
    #COUN:SENS
    #queries or sets the sensitivity of the trigger (i.e. hysteresis)
    def do_get_sensitivity(self):
        return float(self._phy.ask(":COUN:SENS?\n"))
    
    def do_set_sensitivity(self,value):
        self._phy.write(":COUN:SENS " + str(value) + "\n")
    
    #COUN:MEAS?
    #queries frequency, period, duty cycle, pos. and neg. pulse width
    #results come together, we need to split them
    def do_get_frequency(self):
        temp=self._phy.ask(":COUN:MEAS?\n")
        return float(temp.split(',')[0])
    
    def do_get_period(self):
        temp=self._phy.ask(":COUN:MEAS?\n")
        return float(temp.split(',')[1])
    
    def do_get_duty_cycle(self):
        temp=self._phy.ask(":COUN:MEAS?\n")
        return float(temp.split(',')[2]) 

    def do_get_pos_width(self):
        temp=self._phy.ask(":COUN:MEAS?\n")
        return float(temp.split(',')[3]) 
     
    def do_get_neg_width(self):
        temp=self._phy.ask(":COUN:MEAS?\n")
        return float(temp.split(',')[4])
    
    #COUN:STATI
    #queries or enables/disables the display of counter statistics
    #however, statistics cannot be read on remote interface
    def do_get_statistics(self):
        return self._phy.ask(":COUN:STATI?\n").strip() == "ON"
    
    def do_set_statistics(self, value):
        if value:
            self._phy.write(":COUN:STATI ON\n")
        else:
            self._phy.write(":COUN:STATI OFF\n")
    
    #COUN:STATI:CLEA
    #clears statistics 
    def do_stats_clear(self):
        self._phy.write(":COUN:STATI:CLEA\n")
        
    #COUN:STATI:DISP
    #queries or sets the statistics display to digital or curve
    def do_get_stats_display(self):
        return self._phy.ask(":COUN:STATI:DISP?\n").strip() == "CURVE"
    
    
    def do_set_stats_display(self, value):
        if value:
            self._phy.write("COUN:STATI:DISP CURVE\n")
        else:
            self._phy.write("COUN:STATI:DISP DIGITAL\n")
    
    