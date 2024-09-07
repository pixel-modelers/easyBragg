# easyBragg
An easy install of simtbx nanoBragg, i.e. [nanoBragg](https://bl831.als.lbl.gov/~jamesh/nanoBragg/) wrappers for python.

To install, see [here](https://smb.slac.stanford.edu/~dermen/easybragg/)


### Testing the build

Try ```python example.py``` to display a simulated pattern:

![example](https://smb.slac.stanford.edu/~dermen/noise_img.png)

If you ran cmake in a CUDA environment, then you will see an additional image displayed, showing the CPU and GPU kernel results are identical, but the GPU kernel runs faster (~100x, depending on the number of pixels, oversample-rate, number of mosaic domains, and number of sources):

![example2](https://smb.slac.stanford.edu/~dermen/cpu_vs_gpu.png)

Most of the nanoBragg tests can be run, for example:

```
python simtbx_project/simtbx/nanoBragg/tst_nanoBragg_cbf_write.py
python simtbx_project/simtbx/nanoBragg/tst_gauss_argchk.py GPU
```

