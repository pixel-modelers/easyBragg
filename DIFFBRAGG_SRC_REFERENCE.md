# diffBragg C++ Source Reference

Concise structural map of the C++ kernel and Python bindings.
For use as context when implementing features across CPU and GPU kernels.

**User preference**: User builds and runs tests themselves. Do NOT run `setup.py build_ext` or test scripts.

## File Overview

| File | Lines | Purpose |
|------|-------|---------|
| `src/util.h` | ~260 | Structs: `images`, `crystal`, `beam`, `detector`, `flags`, `step_arrays` |
| `src/diffBragg.h` | ~380 | Class declaration: `diffBragg` (extends `nanoBragg`), derivative managers |
| `src/diffBragg.cpp` | ~2450 | Constructor, refine/fix system, kernel entry, geometry packing |
| `src/diffBragg_cpu_kernel.cpp` | ~1400 | CPU forward model + all analytical gradients |
| `src/diffBragg_ext.cpp` | ~900 | Boost.Python bindings |
| `src/diffBraggCUDA.cu` | ~735 | CUDA entry: memory mgmt, kernel launch, H2D/D2H copies |
| `src/diffBraggCUDA.h` | ~120 | `diffBragg_cudaPointers` struct (device pointer registry) |
| `src/diffBragg_gpu_kernel.cu` | ~1270 | GPU `__global__` kernel (forward model + gradients) |
| `src/diffBragg_gpu_kernel.h` | ~80 | GPU kernel function prototype |
| `__init__.py` | ~200 | Python wrappers, array validation, convenience methods |

## Refine ID Constants (from hopper_utils.py)

```
ROTX_ID = 0, ROTY_ID = 1, ROTZ_ID = 2
UCELL_ID_OFFSET = 3  (3-8 for a,b,c,alpha,beta,gamma)
NCELLS_ID = 9  (diagonal Na,Nb,Nc)
DETZ_ID = 10
FHKL_ID = 11
ETA_ID = 19
NCELLS_ID_OFFDIAG = 21  (Nd,Ne,Nf)
DIFFUSE_ID = 23
GONIO_ANGLE_ID = 24
BFACTOR_ID = 25
BFACTOR_ANISO_ID = 26  (6-component β11,β22,β33,β12,β13,β23 in fractional hkl)
```

Next free ID: **27**.

## Key Structs (util.h)

### `crystal` (db_cryst)
- `Na, Nb, Nc, Nd, Ne, Nf` — NABC tensor components
- `Bfactor_image` — per-image isotropic B (Ang^2)
- `eig_U, eig_B, eig_O` — orientation, orthogonalization, change-of-basis matrices
- `UMATS_RXYZ[]` — mosaic domain rotation matrices
- `dB_Mats[0-5], dB2_Mats[0-5]` — unit cell derivative matrices
- `FhklLinear[], Fhkl2Linear[]` — linearized structure factors
- `FhklLinear_ASUid[]` — maps linear hkl index to ASU id
- `spot_scale, r_e_sqr, fudge, dmin` — scaling and geometry
- `anisoG, anisoU, dG_dgamma[], dU_dsigma[]` — diffuse scattering tensors

### `flags` (db_flags)
- `no_Nabc_scale` — omit det(NABC) from F_latt
- `refine_Bfactor` — compute B-factor gradient
- `refine_Umat[3], refine_Bmat[6], refine_Ncells[3]` — per-component flags
- `refine_Ncells_def` — off-diagonal Nabc
- `gradient_mode, calc_Fhkl_gradients` — Fhkl gradient early-exit path
- `compute_curvatures` — accumulate second derivatives (Hessian)

### `images` (first_deriv_imgs, second_deriv_imgs)
Per-pixel derivative storage (image_type = vector<double>):
```
Umat[3*Npix], Bmat[6*Npix], Ncells[6*Npix], fcell[Npix],
eta[3*Npix], lambda[2*Npix], panel_rot[3*Npix], panel_orig[3*Npix],
fp_fdp[2*Npix], diffuse_gamma[3*Npix], diffuse_sigma[3*Npix],
gonio_angle[Npix], Bfactor[Npix], Bfactor_aniso[6*Npix],
Fhkl_scale_deriv[Num_ASU], Fhkl_hessian[Num_ASU]
```

## CPU Kernel: `diffBragg_sum_over_steps()` (diffBragg_cpu_kernel.cpp)

### Loop Structure
```
for each pixel (OpenMP parallel):        // line 340
  skip if untrusted
  extract panel, fpixel, spixel
  init per-pixel derivative accumulators (all zeros)
  compute cell_vol, xtal_size

  for each step (oversample x thickness x sources x phi x mosaic):  // line 414
    compute pixel position in lab frame
    compute solid angle (omega_pixel), capture_fraction
    compute incident beam vector, wavelength
    compute scattering vector q = (diffracted - incident)/lambda
    stol = 0.5 * |q|                      // sin(theta)/lambda

    // Orientation matrices
    Bmat_realspace = 1e10 * eig_B          // fractional -> m^-1
    UBOt = U * Bmat * O^T
    if phi: UBOt = Rphi * UBOt             // goniometer rotation
    UBO = (UMATS_RXYZ[mos] * UBOt)^T       // mosaic domain
    Ainv = UBO^-1

    // Reciprocal space coordinates
    H_vec = UBO * (q * 1e-10)              // lab q -> fractional hkl
    h0,k0,l0 = round(H_vec)               // nearest Bragg peak

    // NABC tensor and peak shape
    NABC = [[Na,Nd,Nf],[Nd,Nb,Ne],[Nf,Ne,Nc]]
    delta_H = H_vec - H0
    V = NABC * delta_H
    hrad_sqr = V . V
    F_latt = exp(-hrad_sqr / 0.63 * fudge)   // Gaussian shape
    if (!no_Nabc_scale): F_latt *= det(NABC)  // line 587

    // Structure factor lookup
    F_cell = FhklLinear[h0,k0,l0]
    I_cell = F_cell^2
    Iincrement = s_hkl * I_cell * F_latt^2 * count_scale

    // B-factor (isotropic)                 // line 793-803
    stol_sqr_Ang = stol^2 * 1e-20
    Bfac_term = exp(-Bfactor_image * stol_sqr_Ang)
    Iincrement *= Bfac_term
    if refine_Bfactor:
      dI_Bfactor += Iincrement * (-stol_sqr_Ang)

    // === GRADIENT SECTION (lines 858-1116) ===
    // All follow pattern: dH/dparam -> dV = NABC*dH -> V.dV -> dI
    C = 2/0.63 * fudge

    // Rotation (RotXYZ): dH from dRx,dRy,dRz      lines 865-912
    // Unit cell (B-mat):  dH from dB_Mats[0-5]     lines 913-933
    // Ncells diagonal:    dN -> determ_deriv + shape lines 935-966
    //   if !no_Nabc_scale: determ_deriv = trace(NABC^-1 * dN)
    // Ncells off-diag:    same pattern               lines 968-993
    // Panel origin/rot:   via get_panel_increment()   lines 994-1032
    // F_cell:             dI = 2*F_cell*I_noFcell     lines 1034-1070
    // Eta (mosaic):       dH from UMATS_prime         lines 1072-1095
    // Lambda:             dH from wavelength chain    lines 1097-1116

  end step loop

  // Accumulate to images (lines 1180-1381)
  scale_term = r_e^2 * fluence * spot_scale * polar / Nsteps
  floatimage[pix] = scale_term * I
  d_image.Bfactor[pix] = scale_term * dI_Bfactor
  d_image.Ncells[pix*N + i] = scale_term * Ncells_manager_dI[i]
  // ... similar for all other derivative images

end pixel loop
```

### Key Physics: Scattering Vector and Coordinates

```
q_lab (m^-1)  = (diffracted - incident) / lambda
stol (m^-1)   = 0.5 * |q_lab|               // sin(theta)/lambda
H_vec         = UBO * (q_lab * 1e-10)        // fractional hkl (continuous)
h0,k0,l0      = round(H_vec)                 // nearest integer hkl
delta_H       = H_vec - (h0,k0,l0)           // fractional offset from Bragg

UBO = (U_mosaic * U_cryst * B_realspace * O^T)^T
    where B_realspace = 1e10 * eig_B  (maps fractional -> m^-1 reciprocal space)

Ainv = UBO^-1  (maps lab q -> fractional hkl, used for GAUSS_STAR shape)
```

### Current Isotropic B-factor Implementation
```cpp
// Forward model (line 796-798):
Bfac_term = exp(-Bfactor_image * stol * stol * 1e-20);  // stol in m^-1, B in Ang^2
Iincrement *= Bfac_term;

// Gradient (line 800-802):
if (refine_Bfactor)
    dI_Bfactor += Iincrement * (-stol_sqr_Ang);  // dI/dB = I * (-s^2)

// Image accumulation (line 1300-1301):
d_image.Bfactor[i_pix] = scale_term * dI_Bfactor;
```

## diffBragg.cpp: Key Sections

### Constructor (~line 177)
- Creates derivative manager pools:
  - 3 rot_managers (rotX/Y/Z), 6 ucell_managers, 6 Ncells_managers
  - 3 eta_managers, 3 lambda_managers, 3 origin_managers
  - 3 panel_managers, 3 fcell_managers, 2 fp_fdp_managers
- Packs detector/beam geometry into db_det, db_beam

### refine()/fix()/let_loose() System (~line 901-1114)
Each takes a `refine_id` (int). `refine()` sets `manager->refine_me = true` AND
calls `manager->initialize(Npix_total, compute_curvatures)` to allocate derivative
image storage. `fix()` clears `refine_me` and the corresponding `db_flags` entry.

To add a new parameter:
1. Choose refine_id (next free: 26)
2. Add case to refine()/fix()/let_loose()
3. Add flag to `db_flags` struct
4. Add derivative image to `images` struct

### add_diffBragg_spots() — Kernel Entry (~line 1963)
1. Build step arrays (oversample x thickness x sources x phi x mosaic)
2. Sync refine flags: db_flags.refine_Bmat[], refine_Umat[], etc.
3. Pack db_cryst (Na-Nf, Bfactor, matrices, Fhkl), db_beam (sources, wavelengths)
4. Allocate derivative images (first_deriv_imgs, second_deriv_imgs)
5. Call kernel: `diffBragg_sum_over_steps()` (CPU) or CUDA/Kokkos variant

### Derivative Accessors
```cpp
get_Bfactor_derivative_pixels()      // returns first_deriv_imgs.Bfactor
get_ncells_derivative_pixels()       // returns tuple (Na_deriv, Nb_deriv, Nc_deriv)
get_ncells_def_derivative_pixels()   // returns tuple (Nd_deriv, Ne_deriv, Nf_deriv)
get_derivative_pixels(refine_id)     // generic: rot, ucell, detz, fcell, etc.
```

## Python Bindings (diffBragg_ext.cpp)

### Key Properties
```python
D.no_Nabc_scale       # bool: omit det(NABC) from F_latt
D.Bfactor_image       # float: per-image B-factor (Ang^2)
D.Ncells_abc          # tuple: (Na, Nb, Nc)
D.Ncells_def          # tuple: (Nd, Ne, Nf)
D.Umatrix             # mat3: crystal rotation
D.Bmatrix             # mat3: reciprocal lattice orthogonalization
D.Omatrix             # mat3: change of basis
D.isotropic_ncells    # bool
D.compute_curvatures  # bool
D.spot_scale          # float (inherited from nanoBragg)
D.Fhkl_tuple          # (indices, amplitudes) or (indices, amp_real, amp_imag)
D.use_diffuse         # bool
D.diffuse_gamma       # tuple (ga, gb, gc)
D.diffuse_sigma       # tuple (sa, sb, sc)
D.Num_ASU             # int (read-only): number of unique ASU reflections
```

### Key Methods
```python
D.refine(refine_id)              # enable refinement, allocate gradient storage
D.fix(refine_id)                 # disable refinement
D.let_loose(refine_id)           # enable without re-allocating
D.add_diffBragg_spots()          # run forward model + gradients
D.add_Fhkl_gradients(...)       # compute Fhkl scale factor gradients
D.get_Bfactor_derivative_pixels()         # dI/dB per pixel
D.get_ncells_derivative_pixels()          # (dI/dNa, dI/dNb, dI/dNc)
D.get_ncells_def_derivative_pixels()      # (dI/dNd, dI/dNe, dI/dNf)
D.get_derivative_pixels(refine_id)        # generic accessor
D.get_second_derivative_pixels(refine_id) # Hessian
D.set_value(refine_id, value)    # set parameter value
D.get_value(refine_id)           # get parameter value
D.update_dxtbx_geoms(det, beam, panel_id, ...)  # update geometry
D.vectorize_umats()              # cache mosaic domain matrices
```

## Anisotropic B-factor: Implementation Status

**CPU: COMPLETE** (refine_id=26). **GPU: NOT YET IMPLEMENTED.**

### Physics
```
T(h,k,l) = exp(-(β11·h² + β22·k² + β33·l² + 2·β12·h·k + 2·β13·h·l + 2·β23·k·l))
```
where h,k,l are continuous fractional coords from `H_vec` (inside mosaic domain loop).
Derivatives: `dT/dβ11 = T·(-h²)`, `dT/dβ12 = T·(-2hk)`, etc.
Isotropic equivalence: `β_ij = (B/4) · G*_ij` where G* is reciprocal metric tensor.

### CPU Implementation (DONE)
- `util.h`: `crystal.Bfactor_aniso[6]`, `flags.refine_Bfactor_aniso`, `images.Bfactor_aniso`
- `diffBragg.h`: `Bfactor_aniso[6]` member, `get_Bfactor_aniso_derivative_pixels()` method
- `diffBragg.cpp`: refine/fix/let_loose(26), db_cryst packing, 6*Npix alloc, 6-tuple accessor
- `diffBragg_cpu_kernel.cpp`: forward model + 6 gradients (after isotropic B, before gradient_mode continue)
- `diffBragg_ext.cpp`: `Bfactor_aniso` property (get_Baniso/set_Baniso), method binding
- `phil.py`: Baniso in all 7 phil sections (betas/centers/sigmas/init/mins/maxs/fix)
- `hopper_utils.py`: BFACTOR_ANISO_ID=26, param creation, forward model, gradient extraction, flags
- `hopper_ensemble_utils.py`: refine flag in prep_for_refinement()
- Test: `--perturb-B-aniso` in tst_diffBragg_hopper_refine_Fhkl.py, test 7 in run_tests.py

### Known Issues
- Per-shot Baniso (18 DOF for 3 shots) instead of shared (6 DOF) — causes G-β compensation
- Test passes R1<4% but individual β values don't match GT well (degeneracy with G)
- Physics-based bounds from reciprocal metric tensor greatly improve convergence

---

## GPU Kernel Architecture: `diffBraggCUDA.cu`

### Entry Point: `diffBragg_sum_over_steps_cuda()` (lines 12-637)

| Section | Lines | Description |
|---------|-------|-------------|
| Block/thread config | 27-39 | Env vars `DIFFBRAGG_NUM_BLOCKS`, `DIFFBRAGG_THREADS_PER_BLOCK` |
| Device selection | 41-49 | `cudaSetDevice` |
| Allocation guard | 55-73 | Checks `Npix_to_model` vs `npix_allocated` for realloc |
| Source reallocation | 76-95 | Dynamic realloc if `number_of_sources` changed |
| **Main allocation block** | 102-225 | All `cudaMallocManaged` calls, guarded by `!cp.device_is_allocated` |
| Lazy Bfactor alloc | 228-230 | Post-allocation lazy alloc for Bfactor deriv images |
| **Host-to-device copies** | 242-432 | Write data to unified memory (FORCE_COPY=true, always runs) |
| **Kernel launch** | 461-528 | `gpu_sum_over_steps<<<numblocks, blocksize>>>()` ~80 args |
| Synchronize | 530-541 | `cudaDeviceSynchronize()` + timing |
| **Device-to-host copies** | 545-627 | Read results from unified memory to host structs |
| `freedom()` | 640-734 | Deallocation: frees all GPU memory |

### Isotropic Bfactor in CUDA Entry (pattern to follow for aniso):

```
Allocation (186-188):   cudaMallocManaged(&cp.cu_d_Bfactor_images, Npix*1*sizeof(CUDAREAL))
Lazy alloc (228-230):   same, guarded by NULL check
Kernel arg (527):       db_cryst.Bfactor_image, db_flags.refine_Bfactor, cp.cu_d_Bfactor_images
D2H copy (552-555):     d_image.Bfactor[i] = cp.cu_d_Bfactor_images[i]
Free (663):             cudaFree(cp.cu_d_Bfactor_images)
```

### Memory Pattern for Derivative Images
```
cudaMallocManaged(&ptr, Npix_to_allocate * NUM_COMPONENTS * sizeof(CUDAREAL))
```
Component counts: Bfactor=1, Umat=3, Bmat=6, Ncells=6, fp_fdp=2, diffuse=3.
**Aniso B needs: `Npix * 6`**.

### Device Pointer Struct: `diffBragg_cudaPointers` (diffBraggCUDA.h)
All GPU pointers live here. Relevant: `cu_d_Bfactor_images=NULL` (line 28).
**Add**: `cu_d_Bfactor_aniso_images=NULL`.

---

## GPU Kernel: `gpu_sum_over_steps()` (diffBragg_gpu_kernel.cu)

### Structure Map

| Section | Lines | Description |
|---------|-------|-------------|
| Kernel signature | 12-82 | `__global__` function, ~80 parameters |
| **Shared memory decls** | 84-153 | `__shared__` vars for block-level caching |
| **Thread-0 init** | 154-285 | `if (threadIdx.x==0)` — sets shared vars, computes Amat_init, Ainv, NABC |
| `__syncthreads()` | 304 | Barrier before pixel loop |
| **Pixel loop** | 306-1266 | `for (i_pix=tid; i_pix < Npix; i_pix += stride)` |
| — Trusted check | 308-311 | Skip untrusted pixels |
| — Gradient coefs | 317-327 | `deriv_coef`, `hessian_coef` |
| — Per-pixel accumulators | 339-365 | Zero-init `_I`, `dI_Bfactor`, all `dI_*` |
| — **Inner loops** | 367-1054 | Nested: subS→subF→thick→source→phi→mosaic |
| —— Detector geometry | 370-422 | Pixel position, omega_pixel, capture_fraction |
| —— Source loop | 424-438 | Incident beam, lambda, source intensity |
| —— Polarization | 447-470 | For gradient mode |
| —— Scattering vector | 472-482 | q_vec, stol, **Bfac_term = exp(-B*stol²*1e-20)** |
| —— Phi/gonio loop | 490-509 | Goniometer rotation |
| —— **Mosaic domain loop** | 512-1049 | Core: UBO, H_vec, lattice factor, Fcell |
| ———— H_vec computation | 521-523 | `_h, _k, _l` = continuous fractional coords |
| ———— Lattice factor | 534-560 | Square or Gaussian peak shape |
| ———— Fcell lookup | 568-579 | FhklLinear table |
| ———— Fhkl gradient path | 671-687 | atomicAdd to Fhkl_scale_deriv (gradient_mode) |
| ———— **Iincrement *= Bfac_term** | 691 | Isotropic B applied |
| ———— `gradient_mode continue` | 698-699 | **SKIPS all deriv accum below** |
| ———— `_I += Iincrement` | 700 | Forward model accumulation |
| ———— **Bfactor gradient** | 701-703 | `dI_Bfactor += Iincrement * (-stol²)` |
| ———— Other gradients | 711-987 | diffuse, fp_fdp, Umat, Bmat, Ncells, etc. |
| — **Post-loop scaling** | 1058-1121 | `_scale_term`, write `floatimage` |
| — **Derivative writes** | 1130-1264 | Write `dI_*` × `_scale_term` to output images |
| —— Bfactor write | 1136-1138 | `d_Bfactor_images[i_pix] = _scale_term * dI_Bfactor` |

### Critical: Isotropic vs Anisotropic B Placement

**Isotropic B** (`Bfac_term`): Computed at line 480 inside **source loop** (depends on `stol` only).
Applied at line 691 inside **mosaic loop**.

**Anisotropic B** (to add): Must be computed inside **mosaic domain loop** (depends on `_h, _k, _l`
from H_vec at lines 521-523). Place between line 691 (isotropic B applied) and line 698
(`gradient_mode continue`).

### Key Variable Names in GPU Kernel
- `_h, _k, _l` — continuous fractional coords (lines 521-523, inside mosaic loop)
- `Iincrement` — accumulated intensity for current step
- `_I` — total pixel intensity (accumulated across all steps)
- `s_Bfactor_image` — shared memory copy of isotropic B value
- `s_refine_Bfactor` — shared memory copy of refine flag

### GPU vs CPU Kernel Differences
| Aspect | CPU Kernel | GPU Kernel |
|--------|-----------|------------|
| Loop structure | Single flat `i_step` loop indexing step arrays | 6 nested loops (subS→subF→thick→source→phi→mosaic) |
| Parallelism | OpenMP over pixels | CUDA threads over pixels |
| Shared state | Stack variables | `__shared__` memory (thread-0 init + syncthreads) |
| Bfac_term location | After mosaic loop (line ~800) | Inside source loop (line 480), applied in mosaic loop (691) |
| Fhkl gradients | gradient_mode continue at line ~863 | gradient_mode continue at line 699 |
| Memory | Direct host arrays | Unified memory (cudaMallocManaged) |

---

## GPU Aniso B Implementation Checklist

### 1. `diffBraggCUDA.h` — Add device pointer
```cpp
CUDAREAL* cu_d_Bfactor_aniso_images=NULL;  // near line 28
```

### 2. `diffBragg_gpu_kernel.h` — Add 3 kernel params
```cpp
CUDAREAL* Bfactor_aniso,        // 6-element array (β11..β23)
bool refine_Bfactor_aniso,
CUDAREAL* d_Bfactor_aniso_images
```

### 3. `diffBraggCUDA.cu` — 5 modifications
- **Allocation** (~188): `cudaMallocManaged(&cp.cu_d_Bfactor_aniso_images, Npix*6*sizeof(CUDAREAL))`
- **Lazy alloc** (~230): NULL guard pattern
- **Host-to-device**: Pass `db_cryst.Bfactor_aniso` (already in unified memory via db_cryst)
- **Kernel launch** (~527): Add 3 new args
- **D2H copy** (~555): Loop `6*Npix` copying to `d_image.Bfactor_aniso[]`
- **freedom()** (~663): `cudaFree(cp.cu_d_Bfactor_aniso_images)`

### 4. `diffBragg_gpu_kernel.cu` — 6 modifications
- **Kernel params** (line 82): Add 3 params
- **Shared memory** (~89): `__shared__ bool s_refine_Bfactor_aniso; __shared__ CUDAREAL s_Bfactor_aniso[6];`
- **Thread-0 init** (~157): Copy flag + 6 values to shared
- **Per-pixel accum** (~365): `double dI_Bfac_aniso[6] = {0,...};`
- **Forward + gradient** (between lines 691-698, inside mosaic loop):
  ```cpp
  // After Iincrement *= Bfac_term (line 691), before gradient_mode continue (698):
  bool use_Baniso = (s_Bfactor_aniso[0]!=0 || ... || s_refine_Bfactor_aniso);
  if (use_Baniso) {
      CUDAREAL Baniso_term = s_Bfactor_aniso[0]*_h*_h + s_Bfactor_aniso[1]*_k*_k
                           + s_Bfactor_aniso[2]*_l*_l + 2*s_Bfactor_aniso[3]*_h*_k
                           + 2*s_Bfactor_aniso[4]*_h*_l + 2*s_Bfactor_aniso[5]*_k*_l;
      Iincrement *= exp(-Baniso_term);
  }
  ```
  Also apply in Fhkl gradient path (~671-687): multiply dfhkl by `exp(-Baniso_term)`.
  Gradient accumulation (after line 703, non-gradient_mode path):
  ```cpp
  if (s_refine_Bfactor_aniso) {
      dI_Bfac_aniso[0] += Iincrement * (-_h*_h);  // etc for all 6
  }
  ```
- **Post-loop write** (~1138):
  ```cpp
  if (s_refine_Bfactor_aniso)
      for (int i=0;i<6;i++) d_Bfactor_aniso_images[i*Npix+i_pix] = _scale_term * dI_Bfac_aniso[i];
  ```

### 5. No Python-side changes needed (already done for CPU)
