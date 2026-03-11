# Project Reorganization

This folder tracks the functional reorganization of the IIHS project.

Current status:
- Planning completed
- Script moves completed with compatibility wrappers
- Document moves completed with compatibility stubs
- Smoke tests completed for key Python entrypoints
- Node acquisition entrypoints load from the new paths, but live execution is blocked by an expired IIHS authenticated session

Artifacts:
1. `step_01_function_inventory.md`
2. `step_02_target_folder_structure.md`
3. `step_03_keep_hold_delete_plan.md`
4. `step_04_impact_and_migration_plan.md`
5. `step_05_execution_instructions.md`
6. `step_06_execution_results.md`
7. `project_reorg_manifest.json`

Compatibility policy:
- Keep the existing CLI entrypoint names
- Keep root-level wrappers for moved scripts
- Keep root-level doc stubs for moved docs
- Treat deletion candidates as a later cleanup phase, not part of the structural move
