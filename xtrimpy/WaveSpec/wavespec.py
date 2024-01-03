# defines a wave spec object to be displayed
import os
from astropy.convolution import Box1DKernel
from astropy.convolution import convolve, convolve_fft
import numpy as np
from . import sloader

class wavespec_obj:

    def __init__(self, fn, loader=sloader.default):

        self.filename = fn
        self.loader = loader

        self.add = 0.
        self.mult = 1.
        self.color = None
        self.addredshift = 0.
        self.smooth_width = 0
        
        # read file
        wave, spec, error = loader(fn)
        self.wave = wave
        self.spec = spec
        self.error = error

        self.reset()

        self.label = os.path.basename(fn)

        return

    def reset(self):

        self.smooth_width = 0
        self.spec_display = self.spec.copy()
        if self.error is not None:
            self.error_display = self.error.copy()
        else:
            self.error_display = None

        return
    
    def smooth(self, width):
        
        self.smooth_width = width

        if width > 0:
            kernel = Box1DKernel(width)
            self.spec_display = convolve(self.spec, kernel)
            
            if self.error is not None:
                self.error_display = convolve(self.error, kernel) / np.sqrt(width)
        else:
            self.reset()

        return


