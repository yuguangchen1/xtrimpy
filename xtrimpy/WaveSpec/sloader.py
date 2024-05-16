import numpy as np
from astropy.io import fits


def default(fn):

    hdu = fits.open(fn)[0]
    header = hdu.header

    spec = hdu.data

    #Select the appropriate axis.
    naxis = header['NAXIS']
    flag = False
    for i in range(naxis):
        #Keyword entry
        card = "CTYPE{0}".format(i+1)
        if not card in header:
            raise ValueError("Header must contain 'CTYPE' keywords.")
        
        #Possible wave types.
        if header[card] in ['AWAV', 'WAVE', 'VELO', 'Wavelength', 'WAVE-TAB']:
            axis = i+1
            flag = True
            break

    #No wavelength axis
    if flag == False:
        axis = 1

    try:
        #Get keywords defining wavelength axis
        nwav = header["NAXIS{0}".format(axis)]
        wav0 = header["CRVAL{0}".format(axis)]
        card_dw = 'CD{0}_{0}'.format(axis)
        if card_dw not in header:
            card_dw = 'CDELT{0}'.format(axis)
            if card_dw not in header:
                raise ValueError("Wavelength header incomplete.")
        dwav = header[card_dw]
        pix0 = header["CRPIX{0}".format(axis)]

        #Calculate and return
        wave = np.array([wav0 + (i - pix0 + 1) * dwav for i in range(nwav)])

    except:
        raise ValueError("Header must contain a wavelength/velocity axis.")

    return wave, spec, None

def SpitzerIRS(fn):
    from astropy.io import ascii

    tab = ascii.read(fn)

    return tab['wavelength'], tab['flux_density'], tab['error']


def DJA_NIRSpec(fn):

    hdu = fits.open(fn)[1]
    try:
        wave = hdu.data['WAVELENGTH']
        flux = hdu.data['FLUX']
        err = hdu.data['FLUX_ERR']
    except:
        wave = hdu.data['wave']
        flux = hdu.data['flux']
        err = hdu.data['err']

    return wave, flux, err

def ESO_UVES(fn):

    hdu = fits.open(fn)[1]
    wave = hdu.data['WAVE'].flatten()
    flux = hdu.data['FLUX_REDUCED'].flatten()
    err = hdu.data['ERR_REDUCED'].flatten()

    return wave, flux, err

def HIRES(fn):
    hdu = fits.open(fn)[0]
    hdr = hdu.header
    spec = hdu.data
    wave = 10**((np.arange(len(spec)) - hdr['CRPIX1'] + 1) * hdr['CDELT1'] + hdr['CRVAL1'])

    return wave, spec, None

def BPASSv23(fn):
    from astropy.io import ascii
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

    tab = ascii.read(fn)

    class NumberInputDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.initUI()

        def initUI(self):
            self.setWindowTitle('Input a Number')
            self.layout = QVBoxLayout()

            self.label1 = QLabel('Col numbers from 2-{0:d}'.format(len(tab.colnames)))
            self.layout.addWidget(self.label1)

            self.label2 = QLabel('log(Age) = 6+0.1*(n-2)')
            self.layout.addWidget(self.label2)

            self.numberInput = QLineEdit(self)
            self.layout.addWidget(self.numberInput)

            self.okButton = QPushButton('OK', self)
            self.okButton.clicked.connect(self.accept)
            self.layout.addWidget(self.okButton)

            self.setLayout(self.layout)

        def getNumber(self):
            return self.numberInput.text()

    def showNumberInputDialog():
        dialog = NumberInputDialog()
        if dialog.exec_() == QDialog.Accepted:
            return dialog.getNumber()
        return None
    
    number = showNumberInputDialog()
    if number is not None:
        return tab['col1'], tab['col{0:d}'.format(int(number))], None







