# Cryomech_logreader.py driver to parse temperature/pressure logfiles of 
# the Cryomech pulse tube coolers.
# The driver reads the logfile created by the Cryomech diagnostic software 
# and returns the last entry.
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

class Cryomech_logeader(Instrument):

    #Units can be set to either "Metric" (True) or "Imperial" (False) when loading the driver
    #Default is metric.
    #Logfile contains values in Imperial units
    UNITS=True
    
    def __init__(self, name, datafile='', datadirectory='', units='Metric'):
        Instrument.__init__(self, name, tags=['physical'])

        logging.info("Cryomech_logreader: Initializing")

        self._datafile=datafile
        self._datadirectory=datadirectory
        
        if self._datafile == '' and self._datadirectory=='':
            logging.error("Cryomech_logreader: Error: no datadirectory or datafile specified.")
            return False
        
        if units == 'Metric':
            self.UNITS=True
            temp_units='Celsius'
            pressure_units='bar'
        elif units == 'Imperial':
            self.UNITS=False
            temp_units='Fahrenheit'
            pressure_units='psi'
        else:
            logging.error("Cryomech_logreader: Error: invalid units specification. Use Metric or Imperial.")

        self.add_parameter('water_in', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units=temp_units,
                format='%.2f')

        self.add_parameter('water_out', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units=temp_units,
                format='%.2f')
        
        self.add_parameter('he_gas', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units=temp_units,
                format='%.2f')

        self.add_parameter('oil_temperature', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units=temp_units,
                format='%.2f')

        self.add_parameter('motor_current', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='A',
                format='%.1f')

        self.add_parameter('low_pressure', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units=pressure_units,
                format='%.2f')

        self.add_parameter('high_pressure', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units=pressure_units,
                format='%.2f')
        
        self.add_parameter('last_update', type=types.StringType,
                           flags=Instrument.FLAG_GET)
        
        self.add_parameter('filename', type=types.StringType,
                           flags=Instrument.FLAG_GET)                

        self.get_all()        
         
    #Reads all available parameters
    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)
    
    def do_get_water_in(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[3,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        if self.UNITS:
            return self._convert_temp(res[np.size(res)-1])
        return res[np.size(res)-1]

    def do_get_water_out(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[4,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        if self.UNITS:
            return self._convert_temp(res[np.size(res)-1])
        return res[np.size(res)-1]

    def do_get_he_gas(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[5,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        if self.UNITS:
            return self._convert_temp(res[np.size(res)-1])
        return res[np.size(res)-1]

    def do_get_oil_temperature(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[6,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        if self.UNITS:
            return self._convert_temp(res[np.size(res)-1])
        return res[np.size(res)-1]
    
    def do_get_motor_current(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[7,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        return res[np.size(res)-1]

    def do_get_low_pressure(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[1,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        if self.UNITS:
            return self._convert_pressure(res[np.size(res)-1])
        return res[np.size(res)-1]

    def do_get_high_pressure(self):
        try:
            res=np.loadtxt(self.get_filename(),comments='\"',delimiter='\t',usecols=[2,])
        except Exception:
            return np.nan
        if np.size(res) == 0:
            return np.nan
        if self.UNITS:
            return self._convert_pressure(res[np.size(res)-1])
        return res[np.size(res)-1]
    
    def do_get_last_update(self):
        try:
            res=np.loadtxt(self.get_filename(),dtype='str',comments='\"',delimiter='\t',usecols=[0,])
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
            if os.path.isfile(os.path.join(self._datadirectory,f)) and f.startswith('CPTLog') and f.endswith('.txt'):
                temp=os.lstat(os.path.join(self._datadirectory,f))
                if temp[8] > atime:
                    filen= os.path.join(self._datadirectory,f)
                    atime=temp[8]
        return filen
    
    #internal functions
    
    #converts temperature from F to C
    def _convert_temp(self, value):
        return (value-32.0)/1.8
    
    #converts pressure from psi to bar
    def _convert_pressure(self, value):
        return value*0.0689475729