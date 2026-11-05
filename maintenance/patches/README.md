# Maintained patches

Put only patch files in this directory. Each file must apply cleanly, in
lexical order, to the exact upstream tag selected by the publish workflow.

The normal state is **no patch files**. That keeps `wb_*.py`, `dashboard.html`
and `Dockerfile` byte-for-byte identical to the upstream stable release. The
workflow verifies that state with `git diff --exit-code`.

Patch rules:

1. Give every patch a descriptive number and a corresponding entry in
   `maintenance/README.md`, including source, purpose, and verification.
2. A patch must be minimal and must not overwrite the whole source tree.
3. Use unified diffs created with `git diff --binary`.
4. Never include credentials, account IDs, usage logs, generated output, or
   local absolute paths.
5. Remove a patch from both this directory and the maintenance record once an
   upstream release includes the same fix.

The image is always built from the upstream tag. This directory is the only
place where a fork-specific source adjustment may enter the build.
