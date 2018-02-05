# avs47_logreader.py driver to parse temperature logfiles of 
# the AVS47 bridge in configurations shipped by Leiden Cryogenics.
# the driver parses the logfile written by TC.vi and returns the last entry.
# if datafile is not given, the driver looks for the newest logfile in the directory provided.
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
import types
import logging
import json

class avs47_jsonreader(Instrument):
    
    def __init__(self, name, datafile=''):
        Instrument.__init__(self, name, tags=['physical'])

        logging.info("avs47_jsonreader: Initializing")

        self._datafile=datafile
        
        if self._datafile == '':
            logging.error("avs47_jsonreader: Error: no datafile specified.")
            return False
        '''
        self.add_parameter('resistance_CH', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                channels=(0,7),
                units='Ohm',
                format='%.3g')

        self.add_parameter('temperature_CH', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                channels=(0,7),
                units='mK',
                format='%.4f')
        
        self.add_parameter('heater_CS', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                channels=(0,3),
                units='mA',
                format='%.4f')
        '''
        self.add_parameter('temperature_MC', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='mK',
                format='%.4f')       

        self.add_parameter('heater_MC', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='mA',
                format='%.4f')   
    
               
        self.add_parameter('last_update', type=types.StringType,
                           flags=Instrument.FLAG_GET)
        
        self.add_parameter('filename', type=types.StringType,
                           flags=Instrument.FLAG_GET)                

        self.get_all()        
         
    #Reads all available parameters
    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)
    
    def do_get_filename(self):
        return self._datafile
    
    def do_get_temperature_MC(self):
        with open(self._datafile, 'r') as logfile:
            j = json.load(logfile)
            return float(j['Probe MC'][-1])
    
    def do_get_heater_MC(self):
        with open(self._datafile, 'r') as logfile:
            j = json.load(logfile)
            return float(j['I3 - MC'][-1])
        
    def do_get_last_update(self):
        with open(self._datafile, 'r') as logfile:
            j = json.load(logfile)
            return j['Date1'][-1]
    