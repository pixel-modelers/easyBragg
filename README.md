# easyBragg
An easy install of simtbx nanoBragg, i.e. [nanoBragg](https://bl831.als.lbl.gov/~jamesh/nanoBragg/) wrappers for python.

# Install for Linux

This has been tested on Debian 12 (bookworm) and SUSE 15. It will likely work on intel macs, but unsure about M1 etc.

#### Getting conda

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash ./Miniconda3-latest-Linux-x86_64.sh -b -u -p $PWD/simforge
source simforge/etc/profile.d/conda.sh
```

#### Building

```
conda create -n simtbx conda-forge::cctbx-base python=3.9 -y
conda activate simtbx
conda install conda-forge::dxtbx -y
git clone --recurse-submodules https://github.com/pixel-modelers/easyBragg.git
cd easyBragg
./build.sh
export PYTHONPATH=$PWD/simtbx_project:$PWD/ext
```

Note, at each fresh login one should source conda, activate simtbx env, and set `PYTHONPATH`. For that, create an env script:

<details>
  <summary>`setup_ezbragg.sh`</summary>

```
SIMFORGE=/path/to/simforge
EASYBRAGG=/path/to/easyBragg
source $SIMFORGE/etc/profile.d/conda.sh
conda activate simtbx
export PYTHONPATH=${EASYBRAGG}/simtbx_project:${EASYBRAGG}/ext
```

Hence, at login run `source /path/to/setup_ezbragg.sh`.

</details>

Try ```python example.py``` to display a simulated pattern:

![example](https://smb.slac.stanford.edu/~dermen/simtbx_example.png)

Some of the nanoBragg tests can be run, for example:

```
python simtbx_project/simtbx/nanoBragg/tst_nanoBragg_cbf_write.py
```
