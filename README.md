# XTRIM
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
The line list can be customized, by copying and modifing the [line_list.dat](https://github.com/yuguangchen1/xtrimpy/examples/line_list.dat). 
The first and second columns are wavelengths and labels. Note that the labels cannot contain empty spaces. Additional plotting options for `plt.step()` can be specified similar to
```
3727.4	[OII]   color='green' ls=':'
```
