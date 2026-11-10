# Patch 0_5_28 — CI follows consolidated main

Candidate `0_5_28`, previous `0_5_27`, accepted baseline `0_5_0`, branch `main`.

The earlier candidate branch and the newer 3D feature branch have both been incorporated into main without rewriting any commits. The existing GitHub Actions pipeline had only listened for pushes to the 3D feature branch; its push trigger now listens to main. The Windows CI steps themselves are unchanged.

Validation: confirm a main push runs the full Windows CI checks, inspect VERSION, run scripts/check_structure.py, and validate Windows startup / ESP separately. No application runtime behavior, traffic safety logic, or physical output changes. Explicit owner PASS is still required.
