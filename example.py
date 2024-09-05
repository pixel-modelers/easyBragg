from simtbx.nanoBragg import nanoBragg
import pylab as plt

N = nanoBragg()
N.default_F=1
N.Ncells_abc=10,10,10
N.add_nanoBragg_spots()
img = N.raw_pixels.as_numpy_array()
N.adc_offset_adu = img.max()*0.1
N.show_params()
N.add_noise()
m = img.mean()
s = img.std()
vmin=m-s
vmax=m+4*s
plt.imshow(img, vmax=vmax, vmin=vmin, cmap="gray_r")
plt.show()

