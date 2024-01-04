# XTRIM
![alt text](xtrimpy/lib/xtrim_icon.png)
Light-weight spectroscopic analysis and identification tool

Designed and maintained by Yuguang Chen

For more information, visit [GitHub](https://github.com/yuguangchen1/xtrimpy).

## Shortcuts:

- 'a': draw a zoom box
- 'b': set the y-baseline at flux=0
- 'c': reset the plotting range
- 'd': delete the nearest trim line
- 'e': calculate an equivalent width
- 'i': zoom in on x-axis
- Shift+'i': zoom in on y-axis
- 'k': fit a Gaussian function
- 'm': mark a rest wavelength and calculate redshift
- 'o': zoom out on x-axis
- Shift+'o': zoom out on y-axis
- 'r': reposition the nearest trim line
- 's': smooth all spectra
- 't': add a trim line
- '+': pan right
- '-': pan left
- '''': pan up
- '/': pan down

## Custom line list:
The line list can be customized, by copying and modifing the [line_list.dat](examples/line_list.dat). 
The first and second columns are wavelengths and labels. Note that the labels cannot contain empty spaces. 
Additional plotting options for `plt.step()` can be specified similar to:
```
3727.4	[OII]   color='green' ls=':'
```

## Custom loading functions:
The default reading function reads spectra from the first extension of FITS files and calculate wavelengths from the headers. 
You can add custom functions in `WaveSpec.sloader`, by defining a function that takes a file name and returns `wavelength, flux, error`. 
If the spectrum does not have a corresponding error spectrum, replace `error` with `None`. 
After restart, the newly added function will appear in the `File > Open with...` drop down menu. 

Bug reports and suggestions are welcome!

