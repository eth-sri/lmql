This directory contains support files for `flake.nix`, which is packaging to allow LMQL and its dependencies to be installed anywhere [Nix](https://nixos.org/) is available, even if Python or Node.js wasn't previously available at all!

This includes installation of a copy of llama.cpp.

---

# Usage Summary

A local LMQL playground instance can be started with:

```console
$ nix run github:eth-sri/lmql#playground
```

Similarly, a shell can be started with LMQL's dependencies available:

```console
$ nix develop github:eth-sri/lmql#
```

If one is in a working tree, one can use `.#playground` -- with `.` in place of the `github:` address.

Using just a `#` at the end loads the default target; putting a name after it specifies that non-default item; so to use the `minimal` devShell instead of the default one, from the current source tree, one can run `nix develop .#minimal`. (`minimal` in this case is a shell that doesn't actually provide Python library dependencies, but does provide `poetry`, `poetry2nix`, and other tools needed to _update_ dependencies).

(Note that `#` is a comment character in POSIX-family shells only when not part of a previously-started string; any syntax highlighting that indicates otherwise is wrong.)

---

# Maintenance

## Theory and Background

All software builds in Nix ("derivations") are addressed by a hash of their inputs and the operations performed on those inputs to construct the build. This has a few effects:

- All Nix builds are, if not 100% binary-reproducible, so close to reproducible as to be meaningfully equivalent.
- Nix has stronger requirements in specification of input versions that conventional build systems: A build (on Linux) is sandboxed to be unable to access software that wasn't included in its hash (or to preclude network access at build time, _except_ when performing a step where the output hash is known ahead-of-time).

Not all build systems pin hashes; those that don't thus require extra metadata to be stored to model them in Nix. For example, Python's setuptools wasn't designed with this requirement, but the newer Python build system Poetry _was_. Consequently, we have a `scripts/flake.d/pyproject.toml` file that's used to construct a `poetry.lock` with exact hashes of Python build dependencies. Similarly, where dependencies with Rust components don't include a `Cargo.lock` file in their own source tree, we need to store a lockfile for them.

## Practice

There are generally two classes of common maintenance expected: Updating the flake inputs (such as nixpkgs, from which definitions for the Python interpreter, Rust compiler, and other underlying system dependencies are taken), and updating the Python dependencies. We're going to start with the former.

- Updating the Nix `flake.lock` itself can be done either wholesale, or with individual inputs in mind.

  To update _all_ inputs, one runs:

  ```console
  $ nix flake update
  ```

  To update only a single input (in this case `nixpkgs`):

  ```console
  $ nix flake lock --update-input nixpkgs
  ```

  One also might frequently want to update the llama.cpp flake:

  ```console
  $ nix flake lock --update-input llamaDotCpp
  ```

- Updating Python dependencies in `setup.cfg` also calls for updating `flake.d/poetry.lock`. This can be done as follows:

  ```console
  $ nix develop .#minimal -c sh -c 'cd flake.d && poetry lock --no-update'
  ```

  If there are optional dependencies that one wants to pull in, they can explicitly be added to `pyproject.toml` before running the above operation.

- When adding new Python dependencies, attempts to build them in the Nix sandbox may fail if those dependencies use software at build time where they have build but not runtime dependencies on other packages; this is very common for `setuptools`, for example. In `flake.d/overrides.nix` there is a `buildOps` attribute set where one can describe updates to perform to package definitions before building them. To add `setuptools`, for example, one might use `my-new-package = addBuildInputs [ "setuptools" ];`. To add a Rust build toolchain, one might use `my-new-package = asRustBuild;`.

  When adding a Rust build toolchain, there's one additional complication possible: Well-behaved projects check in their `Cargo.lock` files so the exact, hash-addressed versions of their build-time dependencies can be found. Some projects don't do this, however; to allow Nix to download these projects' dependencies, a `Cargo.lock` needs to be provided for them. The `asRustBuild` helper checks in `flake.d/cargo-deps/<NAME>-<VERSION>-Cargo.lock` for a lockfile when building any package; if a package that requires a Rust toolchain requires dependencies and doesn't include a lockfile, you can try to build it yourself and copy the `Cargo.lock` file into that location to address this.
