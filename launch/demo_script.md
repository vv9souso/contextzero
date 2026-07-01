# Demo Script

1. Open `examples/messy_repo_big`.
2. Run `contextzero demo`.
3. Show the screenshot summary.
4. Open `.contextzero/current_state.md`.
5. Open `.contextzero/read_map.json`.
6. Run `contextzero session-bootstrap examples/messy_repo_big "deployment check"`.
7. Point out stale files to avoid and read-first files.
8. Run `contextzero remember examples/messy_repo_big --type deployment --text "Current production deployment source of truth is docs/production_deploy_current.md." --tags deployment,current`.
9. Run `contextzero recall examples/messy_repo_big deployment`.
