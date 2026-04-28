#!/usr/bin/env python
"""
Test runner for simtbx (nanoBragg + diffBragg).

Usage:
    python run_tests.py                     # run all CPU tests
    python run_tests.py --kokkos            # also run kokkos/GPU tests
    python run_tests.py --filter ncells     # only tests matching 'ncells'
    python run_tests.py --filter hopper --parallel 4   # run in parallel
    python run_tests.py --list              # just list tests, don't run
    python run_tests.py --diffBragg-only    # skip nanoBragg tests
    python run_tests.py --quick             # subset of fast tests
"""
from __future__ import absolute_import, division, print_function
import subprocess
import sys
import os
import time
import argparse
from multiprocessing import Pool

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SIMTBX = os.path.join(SCRIPT_DIR, "simtbx_project", "simtbx")
D = SIMTBX  # alias matching the $D convention

# ---------------------------------------------------------------------------
# Test definitions  (each entry is either a path string or [path, args...])
# ---------------------------------------------------------------------------

nb_tst_list = [
    "$D/nanoBragg/tst_nanoBragg_minimal.py",
    "$D/nanoBragg/tst_nanoBragg_mosaic.py",
    "$D/nanoBragg/tst_gaussian_mosaicity.py",
    "$D/nanoBragg/tst_gaussian_mosaicity2.py",
    "$D/nanoBragg/tst_nanoBragg_cbf_write.py",
    "$D/nanoBragg/tst_multisource_background.py",
    "$D/nanoBragg/tst_anisotropic_mosaicity.py",
]

db_tst_list_nonCuda = [
    "$D/diffBragg/tests/tst_diffBragg_utils.py",
    "$D/diffBragg/tests/tst_diffBragg_structure_factors.py",
]

db_tst_list_onlyGPU = [
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb eta --kokkos"],
]

db_tst_list = [
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G --auto-sigma"],
    "$D/diffBragg/tests/tst_diffBragg_Fhkl_complex.py",
    "$D/diffBragg/tests/tst_hopper_usecase.py",
    "$D/diffBragg/tests/tst_diffBragg_change_of_basis.py",
    "$D/diffBragg/tests/tst_diffBragg_update_dxtbx_geoms.py",
    "$D/diffBragg/tests/tst_diffBragg_deriv_rois.py",
    "$D/diffBragg/tests/tst_diffBragg_detdist_derivatives.py",
    "$D/diffBragg/tests/tst_diffBragg_nanoBragg_congruency.py",
    "$D/diffBragg/tests/tst_diffBragg_ncells_property.py",
    "$D/diffBragg/tests/tst_diffBragg_ncells_offdiag_property.py",
    ["$D/diffBragg/tests/tst_diffBragg_ncells_offdiag_property.py", "--idx 1"],
    ["$D/diffBragg/tests/tst_diffBragg_ncells_offdiag_property.py", "--idx 2"],
    # Cholesky decomposition of NABC
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 0"],
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 1"],
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 2"],
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 3"],
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 4"],
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 5"],
    # Per-image B-factor
    "$D/diffBragg/tests/tst_diffBragg_Bfactor_property.py",
    ["$D/diffBragg/tests/tst_diffBragg_Bfactor_property.py", "--Bfactor 5"],
    ["$D/diffBragg/tests/tst_diffBragg_Bfactor_property.py", "--Bfactor 10"],
    # Anisotropic B-factor (6-component tensor)
    "$D/diffBragg/tests/tst_diffBragg_Bfactor_aniso_property.py",
    ["$D/diffBragg/tests/tst_diffBragg_ncells_property_anisotropic.py", "--idx 0"],
    ["$D/diffBragg/tests/tst_diffBragg_ncells_property_anisotropic.py", "--idx 1"],
    ["$D/diffBragg/tests/tst_diffBragg_ncells_property_anisotropic.py", "--idx 2"],
    ["$D/diffBragg/tests/tst_diffBragg_unitcell_property.py", "--crystalsystem tetragonal"],
    ["$D/diffBragg/tests/tst_diffBragg_unitcell_property.py", "--crystalsystem hexagonal"],
    ["$D/diffBragg/tests/tst_diffBragg_unitcell_property.py", "--crystalsystem monoclinic"],
    ["$D/diffBragg/tests/tst_diffBragg_lambda_coefficients.py", "--idx 0"],
    ["$D/diffBragg/tests/tst_diffBragg_lambda_coefficients.py", "--idx 1"],
    "$D/diffBragg/tests/tst_diffBragg_regions_of_interest.py",
    "$D/diffBragg/tests/tst_diffBragg_rotXYZ.py",
    ["$D/diffBragg/tests/tst_diffBragg_rotXYZ_deriv.py", "--curvatures --rotidx 0"],
    ["$D/diffBragg/tests/tst_diffBragg_rotXYZ_deriv.py", "--curvatures --rotidx 1"],
    ["$D/diffBragg/tests/tst_diffBragg_rotXYZ_deriv.py", "--curvatures --rotidx 2"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb crystal"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb Nabc"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb G"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb detz_shift"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb crystal Nabc G"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb crystal Nabc G detz_shift"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb Nabc G"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb spec"],
    ["$D/diffBragg/tests/tst_diffBragg_Fcell_deriv.py", "--curvatures"],
    ["$D/diffBragg/tests/tst_diffBragg_eta_derivs.py", "--curvatures"],
    "$D/diffBragg/tests/tst_diffBragg_eta_derivs.py",
    ["$D/diffBragg/tests/tst_diffBragg_eta_derivs.py", "--aniso 0"],
    ["$D/diffBragg/tests/tst_diffBragg_eta_derivs.py", "--aniso 1"],
    ["$D/diffBragg/tests/tst_diffBragg_eta_derivs.py", "--aniso 2"],
    ["$D/diffBragg/tests/tst_diffBragg_panelXY_derivs.py", "--panel x"],
    ["$D/diffBragg/tests/tst_diffBragg_panelXY_derivs.py", "--panel y"],
    ["$D/diffBragg/tests/tst_diffBragg_panelXY_derivs.py", "--panel z"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 0 --gamma 100 125 150"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 0 --gamma 100 125 150 --orientation 1"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 1 --gamma 100 125 150"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 2 --gamma 100 125 150"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 0 --gamma 100 125 150 --grad sigma --sigma 1 2 3"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 0 --gamma 100 125 150 --grad sigma --sigma 1 2 3 --orientation 1"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 1 --gamma 100 125 150 --grad sigma --sigma 1 2 3"],
    ["$D/diffBragg/tests/tst_diffBragg_diffuse_properties.py", "--idx 2 --gamma 100 125 150 --grad sigma --sigma 1 2 3"],
    # Multi-image rotation refinement
    ["$D/diffBragg/tests/tst_rotation_refinement.py", "--perturb crystal"],
    ["$D/diffBragg/tests/tst_rotation_refinement.py", "--perturb crystal Nabc G"],
]

gpu_tst_list = [
    ["$D/nanoBragg/tst_gauss_argchk.py", "GPU"],
    ["$D/gpu/tst_gpu_multisource_background.py", "context=kokkos_gpu"],
    ["$D/gpu/tst_exafel_api.py", "context=kokkos_gpu"],
    ["$D/gpu/tst_shoeboxes.py", "context=kokkos_gpu"],
]

# Fhkl refinement suite: exercises Cholesky Nabc, B-factor, auto-sigma, multi-shot
fhklref_tst_list = [
    # 1. Baseline Fhkl-only (no perturbation of G/Nabc/B)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2"],
    # 2. Fhkl + G joint refinement (multi-shot ensemble)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G"],
    # 3. Fhkl + G + Nabc (6-term Cholesky tensor, multi-shot)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G Nabc"],
    # 4. Fhkl + G + auto-sigma (multi-shot, per-Fhkl step sizes)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G --auto-sigma"],
    # 5. Fhkl + G + B-factor (multi-shot, per-image B recovery)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G --perturb-B 2.0"],
    # 6. Everything: Fhkl + G + Nabc + B-factor + auto-sigma (multi-shot)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G Nabc --perturb-B 2.0 --auto-sigma"],
    # 7. Fhkl + G + anisotropic B-factor (multi-shot)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G --perturb-B-aniso"],
    # 8. Fhkl + G + Nabc + anisotropic B-factor (multi-shot)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G Nabc --perturb-B-aniso"],
    # 9. Fhkl + G + anisotropic B-factor + auto-sigma (multi-shot)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G --perturb-B-aniso --auto-sigma"],
    # 10. Everything with aniso B: Fhkl + G + Nabc + aniso B + auto-sigma (multi-shot)
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine_Fhkl.py", "--scale .2 --perturb G Nabc --perturb-B-aniso --auto-sigma"],
    # 11. Hopper->Geometry parameter propagation round-trip (30 configs)
    "$D/diffBragg/tests/tst_hopper_geometry_propagation.py",
]

# A quick subset for fast smoke-testing
quick_tst_list = [
    "$D/diffBragg/tests/tst_diffBragg_utils.py",
    "$D/diffBragg/tests/tst_diffBragg_ncells_property.py",
    "$D/diffBragg/tests/tst_diffBragg_ncells_offdiag_property.py",
    ["$D/diffBragg/tests/tst_diffBragg_cholesky_property.py", "--idx 0"],
    "$D/diffBragg/tests/tst_diffBragg_Bfactor_property.py",
    "$D/diffBragg/tests/tst_diffBragg_Bfactor_aniso_property.py",
    ["$D/diffBragg/tests/tst_diffBragg_rotXYZ_deriv.py", "--curvatures --rotidx 0"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb Nabc"],
    ["$D/diffBragg/tests/tst_diffBragg_hopper_refine.py", "--perturb crystal Nabc G"],
    "$D/diffBragg/tests/tst_diffBragg_nanoBragg_congruency.py",
    #["$D/diffBragg/tests/tst_rotation_refinement.py", "--perturb crystal"],
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_path(entry):
    """Convert a test entry to (script_path, args_list, label)."""
    if isinstance(entry, str):
        script = entry.replace("$D", D)
        return script, [], os.path.relpath(script, SCRIPT_DIR)
    else:
        script = entry[0].replace("$D", D)
        # remaining entries may be single strings with spaces (e.g. "--perturb crystal Nabc G")
        args = []
        for a in entry[1:]:
            args.extend(a.split())
        label = os.path.relpath(script, SCRIPT_DIR) + " " + " ".join(args)
        return script, args, label


import re

_FHKLREF_PATTERNS = [
    re.compile(r"=== Refinement:.*"),
    re.compile(r"\s+Refining:.*"),
    re.compile(r"\s+Fixed:.*"),
    re.compile(r"\s+Options:.*"),
    re.compile(r".*R1.*%.*"),
    re.compile(r".*PASSED.*"),
    re.compile(r".*Shot \d+:.*"),
    re.compile(r"\s+GT:.*"),
    re.compile(r".*multiplicity=\d+:.*"),
    re.compile(r".*Skipping single-shot.*"),
    re.compile(r".*assert.*", re.IGNORECASE),
    re.compile(r".*Error.*", re.IGNORECASE),
    re.compile(r".*Per-shot parameter recovery.*"),
]

def extract_fhklref_summary(output):
    """Extract key diagnostic lines from Fhkl refinement test output."""
    lines = []
    for line in output.splitlines():
        for pat in _FHKLREF_PATTERNS:
            if pat.match(line.rstrip()):
                lines.append(line.rstrip())
                break
    return "\n".join(lines)


def run_one(task):
    """Run a single test. Returns (label, passed, elapsed, output)."""
    script, args, label = task
    cmd = [sys.executable, script] + args
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            cwd=os.path.dirname(script) or ".",
        )
        elapsed = time.time() - t0
        passed = result.returncode == 0
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        passed = False
        output = "TIMEOUT after %.0fs" % elapsed
    except Exception as exc:
        elapsed = time.time() - t0
        passed = False
        output = "EXCEPTION: %s" % exc
    return label, passed, elapsed, output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kokkos", action="store_true",
                        help="Include kokkos/GPU tests")
    parser.add_argument("--filter", type=str, default=None,
                        help="Only run tests whose label contains this substring")
    parser.add_argument("--parallel", "-j", type=int, default=1,
                        help="Number of parallel workers (default: serial)")
    parser.add_argument("--list", action="store_true",
                        help="Just list tests, don't run them")
    parser.add_argument("--diffBragg-only", action="store_true",
                        help="Skip nanoBragg tests")
    parser.add_argument("--quick", action="store_true",
                        help="Run a small fast subset of tests")
    parser.add_argument("--fhklref", action="store_true",
                        help="Run Fhkl refinement suite (Cholesky, B-factor, aniso B, auto-sigma, multi-shot)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print stdout/stderr for failed tests")
    args = parser.parse_args()

    # Build test list
    if args.fhklref:
        tests_raw = list(fhklref_tst_list)
    elif args.quick:
        tests_raw = list(quick_tst_list)
    else:
        tests_raw = []
        if not args.diffBragg_only:
            tests_raw += nb_tst_list
        tests_raw += db_tst_list_nonCuda + db_tst_list
        if args.kokkos:
            tests_raw += gpu_tst_list + db_tst_list_onlyGPU
            # Also run all db_tst_list with --kokkos appended
            for entry in db_tst_list:
                if isinstance(entry, str):
                    tests_raw.append([entry, "--kokkos"])
                else:
                    tests_raw.append(entry + ["--kokkos"])

    # Resolve paths
    tasks = []
    for entry in tests_raw:
        script, test_args, label = resolve_path(entry)
        if not os.path.isfile(script):
            print("WARNING: test not found, skipping: %s" % script)
            continue
        if args.filter and args.filter not in label:
            continue
        tasks.append((script, test_args, label))

    if args.list:
        for i, (_, _, label) in enumerate(tasks, 1):
            print("  %3d. %s" % (i, label))
        print("\n%d tests total" % len(tasks))
        return

    ntests = len(tasks)
    print("=" * 70)
    print("Running %d tests%s" % (ntests, " (parallel=%d)" % args.parallel if args.parallel > 1 else ""))
    print("=" * 70)

    passed_list = []
    failed_list = []
    all_results = []  # (label, passed, elapsed, output)
    t_total = time.time()

    if args.parallel > 1:
        with Pool(args.parallel) as pool:
            for i, result in enumerate(pool.imap_unordered(run_one, tasks), 1):
                label, passed, elapsed, output = result
                all_results.append(result)
                status = "PASS" if passed else "FAIL"
                print("  [%d/%d] %s  %s  (%.1fs)" % (i, ntests, status, label, elapsed))
                if passed:
                    passed_list.append(label)
                else:
                    failed_list.append(label)
                    if args.verbose:
                        print("    --- output ---")
                        for line in output.strip().splitlines()[-20:]:
                            print("    " + line)
                        print("    --- end ---")
    else:
        for i, task in enumerate(tasks, 1):
            result = run_one(task)
            label, passed, elapsed, output = result
            all_results.append(result)
            status = "PASS" if passed else "FAIL"
            print("  [%d/%d] %s  %s  (%.1fs)" % (i, ntests, status, label, elapsed))
            if passed:
                passed_list.append(label)
            else:
                failed_list.append(label)
                if args.verbose:
                    print("    --- output ---")
                    for line in output.strip().splitlines()[-20:]:
                        print("    " + line)
                    print("    --- end ---")

    t_total = time.time() - t_total

    # Summary
    print()
    print("=" * 70)
    print("RESULTS: %d passed, %d failed, %d total  (%.1fs)" % (
        len(passed_list), len(failed_list), ntests, t_total))
    print("=" * 70)

    # Fhklref diagnostic summary — extract key lines for quick review
    if args.fhklref:
        print()
        print("=" * 70)
        print("FHKLREF DIAGNOSTIC SUMMARY")
        print("=" * 70)
        for label, passed, elapsed, output in all_results:
            short_label = label.split("--", 1)[1].strip() if "--" in label else label
            status = "PASS" if passed else "FAIL"
            print("\n--- [%s] %s (%.1fs) ---" % (status, short_label, elapsed))
            summary = extract_fhklref_summary(output)
            if summary:
                print(summary)
            elif not passed:
                # Show last 10 lines on failure when no summary lines matched
                for line in output.strip().splitlines()[-10:]:
                    print(line)
        print("\n" + "=" * 70)

    if failed_list:
        print("\nFAILED:")
        for label in failed_list:
            print("  X  %s" % label)
        sys.exit(1)
    else:
        print("\nAll tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
