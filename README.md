# easyBragg
easy install of simtbx nanoBragg

# Install for Linux

This has been tested on Debian 12 (bookworm). It will likely work on intel macs, but unsure about M1 etc.

```
conda create -n simtbx conda-forge::cctbx-base python=3.9
conda activate simtbx
conda install conda-forge::dxtbx
git clone --recurse-submodules https://github.com/pixel-modelers/easyBragg.git
cd easyBragg
./build.sh
export PYTHONPATH=$PWD/simtbx_project:$PWD/ext
```

Note, the last command should be expanded and done at login.

Try ```python example.py``` to display a simulated pattern.

![example](https://smb.slac.stanford.edu/~dermen/simtbx_example.png)

Some of the nanoBragg tests can be run, for example:

```
python simtbx_project/simtbx/nanoBragg/tst_nanoBragg_cbf_write.py
```
