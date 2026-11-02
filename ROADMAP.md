# Roadmap

These are proposed improvements, not implemented features or promises of delivery.

## Accessible starting points

- Add an English companion to each research workflow in `knowledge/`, preserving evidence boundaries.
- Improve CLI error messages for a missing local index or model, with exact recovery commands.
- Add synthetic tests for ambiguous collection names, missing attachments and mixed Chinese/English queries.
- Document Linux installation results with hardware, Python and dependency versions.

## Retrieval and evidence quality

- Build a redistributable evaluation set using synthetic or appropriately licensed documents.
- Separate held-out evaluation from query-expansion tuning.
- Compare keyword retrieval, hybrid retrieval and an optional local cross-encoder on the same budget.
- Improve table header/row alignment and citation-level evidence audits.
- Add reviewed, experiment-level fields with source spans and change history.

## Integration

- Exercise the documented Claude Desktop, Cursor and VS Code setup in each desktop UI and record versions and image-tool behavior.
- Add a Zotero Local API reader alongside the current read-only SQLite route.
- Make corpus-dependent validation easier to configure for other libraries.
- Add an optional lightweight review interface after the retrieval workflow is stable.

Please open a focused issue with your use case before implementing a large item.
