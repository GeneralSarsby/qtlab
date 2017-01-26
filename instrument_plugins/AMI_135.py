# QTlab driver for American Magnetics 135 liquid helium level meter.
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
import types
import visa
import logging

class AMI_135(Instrument):
    
    def __init__(self, name, address):
              
        logging.info(__name__ + ' : Initializing instrument')
        Instrument.__init__(self, name, tags=['physical'])
                
        self.add_parameter('level', type=types.FloatType,
            flags=Instrument.FLAG_GET, units='')
        self.add_parameter('units', type=types.IntType,
            flags=Instrument.FLAG_GETSET, format_map={0:'cm',1:'inch',2:'%'})
        self.add_parameter('sensor_length', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,units='')
        self.add_parameter('HI_value', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,units='')
        self.add_parameter('LO_value', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,units='')
        self.add_parameter('sampling_interval', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,units='min')

        self._open_serial_connection(address)

        self.get_all()

    def __del__(self):

        logging.debug(__name__ + ' : Deleting instrument')
        self._close_serial_connection()


    def get_all(self):
        
        for p in self.get_parameter_names():
            self.get(p)            
    
    def _open_serial_connection(self, address):
        
        logging.debug(__name__ + ' : Opening serial connection')
        
        self._address = address
        self._visainstrument = visa.instrument(self._address, timeout = 9)
        self._visainstrument.baud_rate = 9600
        self._visainstrument.data_bits = 8
        self._visainstrument.stop_bits = 1
        self._visainstrument.term_chars = '\r\n'
        self._visainstrument.delay = 3
    
    def do_get_level(self):
        
        return float(self._visainstrument.ask("LEVEL"))
    
    def do_get_units(self):
        
        temp = self._visainstrument.ask("UNIT").strip()
        if temp == "C":
            return 0
        elif temp == "I":
            return 1
        elif temp == "%":
            return 2
        else:
            return None
        
    def do_set_units(self, val):
        
        if val == 0:
            self._visainstrument.ask("CM")
        elif val == 1:
            self._visainstrument.ask("INCH")
        else:
            self._visainstrument.ask("PERCENT")
    
    def do_get_sensor_length(self):
        
        return float(self._visainstrument.ask("LENGTH"))    
    
    def do_set_sensor_length(self, val):
        
        self._visainstrument.ask("LENGTH="+"{:0.1f}".format(val))
        self._visainstrument.ask("SAVE")
 
    def do_get_HI_value(self):
        
        return float(self._visainstrument.ask("HI"))    
    
    def do_set_HI_value(self, val):
        
        self._visainstrument.ask("HI="+"{:0.1f}".format(val))
        self._visainstrument.ask("SAVE")    
        
    def do_get_LO_value(self):
        
        return float(self._visainstrument.ask("LO"))    
    
    def do_set_LO_value(self, val):
        
        self._visainstrument.ask("LO="+"{:0.1f}".format(val))
        self._visainstrument.ask("SAVE")
    
    def do_get_sampling_interval(self):
        
        return float(self._visainstrument.ask("INTERVAL"))    
    
    def do_set_sampling_interval(self, val):
        
        self._visainstrument.ask("INTERVAL="+"{:0.1f}".format(val))
        self._visainstrument.ask("SAVE")               
    
    #stops level measurements indefinitely    
    def Hold(self):
        
        self._visainstrument.ask("HOLD")
    
    #restores level measurement with the rate defined by sampling_interval
    def Measure(self):
        
        self._visainstrument.ask("MEASURE")