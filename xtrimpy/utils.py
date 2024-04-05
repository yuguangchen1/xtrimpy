import numpy as np
from scipy import optimize
#import WaveSpec.wavespec

def calc_ew(wavespec, cp):
    # calculate EW and flux. 
    # Note: 1) If error spec is provided, the errors are caculated straightly from
    #   integration without pixel correlation. If smoothing is applied, the 
    #   errors are significantly underestimated. 
    #   2) Errors are approximate for uneven sampling.

    wave = wavespec.wave
    spec = wavespec.spec_display
    espec = wavespec.error_display

    index = (wave >= cp[0]) & (wave < cp[2])
    ctm=(wave[index] - cp[0]) / (cp[2] - cp[0]) * (cp[3] - cp[1]) + cp[1]

    ew = np.trapz(spec[index] / ctm - 1, wave[index])
    if espec is not None:
        ew_sig = np.sqrt(np.trapz((espec[index] / ctm)**2, wave[index]) * (cp[2] - cp[0]))
    else:
        ew_sig = np.nan

    flux = np.trapz(spec[index] - ctm, wave[index])
    if espec is not None:
        flux_sig = np.sqrt(np.trapz(espec[index]**2, wave[index]) * (cp[2] - cp[[0]]))
    else:
        flux_sig = np.nan

    return [ew, ew_sig], [flux, flux_sig]


def gauss(x, area, center, sigma, lin0, lin1):
    # define Gaussian function on linear continuum

    y = (area / np.sqrt(2*np.pi * sigma**2)) * np.exp(-.5*((x-center)/sigma)**2)
    y = y + lin0 + lin1 * (x - center)

    return y

def fit_gauss(wavespec, gl):
    # fit Gaussian profile and measure flux
    wave = wavespec.wave * (wavespec.addredshift + 1)
    spec = wavespec.spec_display * wavespec.mult + wavespec.add
    espec = wavespec.error_display * wavespec.mult + wavespec.add

    index = (wave >= gl[0]) & (wave < gl[1]) * np.isfinite(spec)
    if espec is not None:
        index = index * np.isfinite(espec)
    spec_fit = spec[index]
    if espec is not None:
        espec_fit = espec[index]
    wave_fit = wave[index]
    index = np.argsort(wave_fit)
    wave_fit = wave_fit[index]
    spec_fit = spec_fit[index]
    if espec is not None:
        espec_fit = espec_fit[index]

    # calculate initial guess
    guess = (np.max(spec_fit) - np.min(spec_fit), np.median(wave_fit), (wave_fit[-1] - wave_fit[1])/2, np.median(spec_fit), 0)
    if espec is None:
        popt, pcov = optimize.curve_fit(gauss, wave_fit, spec_fit, p0=guess)
    else:
        popt, pcov = optimize.curve_fit(gauss, wave_fit, spec_fit, p0=guess, \
                                        sigma=espec_fit, absolute_sigma=True)

    specmodel = gauss(wave_fit, *popt)

    flux = [popt[0], np.sqrt(pcov[0, 0])]
    ew = [popt[0] / popt[3], np.sqrt(pcov[0, 0] / popt[3]**2 + popt[0]**2 * pcov[3, 3] / popt[3]**4)]
    center = [popt[1], np.sqrt(pcov[1, 1])]

    return flux, ew, center, wave_fit, specmodel

def parse_line_list(line):
    # Split the line by whitespace
    parts = line.strip().split()

    # Extract mandatory columns
    wave = float(parts[0])  # Convert the first column to float
    label = parts[1]  # The second column is a string

    # Initialize an empty dictionary for kwargs
    kwargs = {}

    # Process the optional parameters
    optional_params = parts[2:]  # All remaining elements in the list
    for param in optional_params:
        # Split each parameter by '=' to separate key and value
        key, value = param.split('=')

        # Remove any quotes and extra whitespace around the key and value
        key = key.strip()
        value = value.strip().strip("'\"")

        # Assign to kwargs dictionary
        kwargs[key] = value

    return wave, label, kwargs

def read_line_list(fn):
    f = open(fn, 'r')

    waves = []
    labels = []
    kws = []
    for line in f:
        if len(line.strip()) == 0:
            continue

        wave, label, kwarg = parse_line_list(line)

        waves.append(wave)
        labels.append(label)
        kws.append(kwarg)

    f.close()

    return waves, labels, kws

