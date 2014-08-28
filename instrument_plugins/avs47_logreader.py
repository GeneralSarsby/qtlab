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
import numpy as np
import os

class avs47_logreader(Instrument):

    def __init__(self, name, datafile='', datadirectory=''):
        Instrument.__init__(self, name, tags=['physical'])

        logging.info("avs47_logreader: Initializing")

        self._datafile=datafile
        self._datadirectory=datadirectory
        
        if self._datafile == '' and self._datadirectory=='':
            logging.error("avs47_logreader: Error: no datadirectory or datafile specified.")
            return False

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
        
        self.add_parameter('last_update', type=types.StringType,
                           flags=Instrument.FLAG_GET)
        
        self.add_parameter('filename', type=types.StringType,
                           flags=Instrument.FLAG_GET)                

        self.get_all()        
         
    #Reads all available parameters
    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)
    
    def do_get_resistance_CH(self, channel):
        try:
            res=np.loadtxt(self.get_filename(),comments='#',delimiter='\t',usecols=[1+channel,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        return res[np.size(res)-1]

    def do_get_temperature_CH(self, channel):
        try:
            res=np.loadtxt(self.get_filename(),comments='#',delimiter='\t',usecols=[10+channel,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        return res[np.size(res)-1]

    def do_get_heater_CS(self, channel):
        try:
            res=np.loadtxt(self.get_filename(),comments='#',delimiter='\t',usecols=[18+channel,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        return res[np.size(res)-1]
    
    def do_get_last_update(self):
        try:
            res=np.loadtxt(self.get_filename(),dtype='str',comments='#',delimiter='\t',usecols=[0,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        return res[np.size(res)-1] 
    
    #returns the logfile to read from:
    #if datafile is specified, then read from there
    #otherwise look for the newest datafile in datadirectory    
    def do_get_filename(self):
        if self._datafile != '':
            return self._datafile
        atime=0
        filen=''
        for f in os.listdir(self._datadirectory):
            if os.path.isfile(os.path.join(self._datadirectory,f)) and f.startswith('LogAVS_') and f.endswith('.dat'):
                temp=os.lstat(os.path.join(self._datadirectory,f))
                if temp[8] > atime:
                    filen= os.path.join(self._datadirectory,f)
                    atime=temp[8]
        return filen