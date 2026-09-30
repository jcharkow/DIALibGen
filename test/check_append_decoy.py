#!/usr/bin/env python
"""End-to-end test of the -mode append_decoy CLI.

Generates a target-only library, appends decoys, and checks the CLI contracts:
  * a decoy is added for every target;
  * an input that already contains decoys is refused unless -redecoy is given;
  * -redecoy drops the old decoys and rebuilds them with the requested method.

Usage: check_append_decoy.py GEN RT_MODEL MS2_MODEL CCS_MODEL FASTA WORKDIR
"""
import subprocess
import sys

import pyarrow.parquet as pq


def decoy_count(path):
    return sum(1 for d in pq.read_table(path, columns=["Decoy"]).to_pydict()["Decoy"] if d)


def run(*args):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main(gen, rt_model, ms2_model, ccs_model, fasta, workdir):
    target = f"{workdir}/append_decoy_target.parquet"
    decoyed = f"{workdir}/append_decoy_decoyed.parquet"
    redecoyed = f"{workdir}/append_decoy_redecoyed.parquet"
    cfg = f"{workdir}/append_decoy_target.json"
    with open(cfg, "w") as f:
        f.write(f'{{"rt_model":"{rt_model}","ms2_model":"{ms2_model}",'
                f'"ccs_model":"{ccs_model}","decoys":"none"}}')

    rc, log = run(gen, "-in", fasta, "-config", cfg, "-out", target)
    assert rc == 0, f"generate failed: {rc}\n{log}"
    n_targets = decoy_count(target)
    assert n_targets > 0, "generated library has no targets"

    rc, log = run(gen, "-mode", "append_decoy", "-in", target, "-out", decoyed,
                  "-generation:decoys", "reverse")
    assert rc == 0, f"append_decoy failed: {rc}\n{log}"
    n_decoyed = decoy_count(decoyed)
    assert n_decoyed == 2 * n_targets, (
        f"expected {2*n_targets} precursors after appending, got {n_decoyed}")

    rc, log = run(gen, "-mode", "append_decoy", "-in", decoyed, "-out", redecoyed,
                  "-generation:decoys", "reverse")
    assert rc != 0 and "already contains" in log and "-redecoy" in log, (
        f"re-decoy without -redecoy should be refused\n{log}")

    rc, log = run(gen, "-mode", "append_decoy", "-in", decoyed, "-out", redecoyed,
                  "-generation:decoys", "shuffle", "-redecoy")
    assert rc == 0, f"redecoy failed: {rc}\n{log}"
    n_redecoyed = decoy_count(redecoyed)
    assert n_redecoyed == 2 * n_targets, (
        f"expected {2*n_targets} precursors after re-decoy, got {n_redecoyed}")

    print(f"append_decoy: {n_targets} targets, appended to {n_decoyed}, "
          f"re-decoyed to {n_redecoyed}: PASS")


if __name__ == "__main__":
    if len(sys.argv) != 7:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
