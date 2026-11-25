# .github

This folder holds the repository's only CI: a daily check that the exercises still work with the current Azure and
AWS tools.

| Path | What it is |
| --- | --- |
| `workflows/cloud-api-check.yml` | The GitHub Actions workflow "Cloud API check". It runs every day at 05:00 UTC and on demand (Actions → Cloud API check → Run workflow). It has two jobs, `azure` and `aws`. |
| `api-check/` | The checker the workflow runs: Python scripts, shell shims, the list of targets and known emulator gaps (`targets.yml`) and the tests. See [api-check/readme.md](api-check/readme.md) for what happens where, with a [flow diagram](api-check/readme.md#what-happens-where). |

Where to look after a run: open the run on the Actions page and scroll to the job summary of each job ("Daily API
check: azure" / "Daily API check: aws"). A red job means something in an exercise no longer works with today's CLI,
IaC tooling or packages, or that the check itself could not run. The summary says which.

The workflow needs no cloud account and no secret: Azure is checked with the local CLI, Bicep, Terraform and the
Cosmos DB emulator, AWS against a local emulator. It only downloads tools and packages from the internet.
