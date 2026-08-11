# TODOs

- [ ] Renaming a workdir silently orphans its store name. `relocate.sh`
      exits at `[ -L .git ]` before `$STORE` is ever compared to
      `readlink .git`, so after an `mv` the symlink still points at the
      old encoded name and no run ever notices. Functionally harmless --
      the absolute symlink stays valid -- but the store name becomes a
      lie, which is the one thing a path-encoded store is for. Hit live
      2026-08-10 renaming `~/claude/bukzor-packaging.kb` ->
      `bukzor-packaging`; fixed by hand (`mv` the store, re-`ln -s`).
      Options: report the mismatch and exit non-zero (matches "don't
      quietly accommodate unknown states"), or detect and re-point. Note
      a rename is indistinguishable from a *copy* until you look, so
      auto-repair could steal a live store.
- [ ] No test covers the `post-index-change` deferral -- the one branch
      where `relocate.sh` must *not* adopt an existing store. Everything
      around it is tested; this is the branch whose failure corrupts an
      in-flight commit.
- [ ] No shellcheck hook in `bukzor-tools/.pre-commit-config.yaml`.
      `relocate.sh` and `hook.sh` are checked by hand.
- [ ] Check whether `docs/dev/testing.kb/recovery-after-deletion.md`
      still pulls its weight next to `reclone-after-workdir-deletion.md`
      -- names are close enough to invite confusion. (2026-07-12
      read-through: they cover distinct entry points -- explicit adopt of
      a ref-less `.git` vs. clone-with-refs merge -- so likely keep both,
      maybe rename.)
