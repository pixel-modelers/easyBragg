import time

from argparse import ArgumentParser
ap = ArgumentParser()
ap.add_argument("--skipGPU", action="store_true")
args = ap.parse_args()

import pylab as plt
import numpy as np


from simtbx.nanoBragg import nanoBragg
from simtbx.nanoBragg import shapetype
from simtbx.nanoBragg import utils
from simtbx.nanoBragg.sim_data import SimData

from dxtbx.model import BeamFactory

# make a beam and detector (DXTBX models)
beam = BeamFactory.simple(1) # wavelength = 1
detector = SimData.simple_detector(100, 0.1, (550,575)) 

# make a miller array
Famp = utils.fcalc_from_pdb(2)

# instantiate the classic nanoBragg simulator
N = nanoBragg(detector, beam)

# make an energy spectrum
# (wavelength, flux) pairs make up the spectrum:
spec = [(0.98,N.flux/4),(0.99,N.flux/4),(1.,N.flux/4),(1.01,N.flux/4)]
flex_beams = utils.get_xray_beams(spec, beam)
N.xray_beams = flex_beams
N.mosaic_spread_deg=0.04
N.mosaic_domains=20
N.Fhkl = Famp
N.Ncells_abc=10,10,10
N.oversample=2
N.xtal_shape = shapetype.Gauss
t = time.time()
N.progress_meter = True
print("Beginning spot simulation ... ")
N.add_nanoBragg_spots()
tcpu = time.time()-t
nonoise_img = N.raw_pixels.as_numpy_array()

# add noise
#N.show_params()
N.adc_offset_adu = nonoise_img.max()*0.1
N.add_noise()
img = N.raw_pixels.as_numpy_array()
print(f"CPU time to simulate noiseless image: {tcpu:.4f} seconds.")

# display the plot
m = img.mean()
s = img.std()
vmin=m-s
vmax=m+4*s
fig,ax = plt.subplots(nrows=1,ncols=1)
ax.imshow(img, vmax=vmax, vmin=vmin, cmap="gray_r")
ax.set_title("noise image")
fig.set_size_inches((4,4))

has_gpu = getattr(N, "add_nanoBragg_spots_cuda") is not None
# do a cuda image for comparison
if has_gpu and not args.skipGPU: 
    print("Running GPU pipeline")
    N.raw_pixels *= 0
    t = time.time()
    N.add_nanoBragg_spots_cuda()
    tgpu = time.time()-t
    test = N.raw_pixels.as_numpy_array()
    print(f"GPU time to simulate noiseless image: {tgpu:.4f} seconds.")
    assert np.allclose(nonoise_img, test)
    m = test.mean()
    s = test.std()
    vmax=m+4*s
    fig2, (ax1,ax2) = plt.subplots(nrows=1,ncols=2) 
    ax1.imshow(nonoise_img, vmax=vmax, vmin=0, cmap="gray_r")
    ax1.set_title(f"CPU ({tcpu:.3f} sec.)")
    ax2.imshow(test, vmax=vmax, vmin=0, cmap="gray_r")
    ax2.set_title(f"GPU ({tgpu:.3f} sec.)")
    fig2.suptitle("Bragg scattering only")
    fig2.set_size_inches((6,3))

plt.show()
print("OK")
