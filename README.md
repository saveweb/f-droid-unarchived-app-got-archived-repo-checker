# is-archived-repo

## Usage

```bash
rm index-v2.json checked.result.json -f # remove index and result files
curl https://f-droid.org/repo/index-v2.json > index-v2.json # download index file
```

```bash
python -m archived_repo_checker.fdroid # run checker, this action is resumable (Ctrl+C to stop, and run again to continue)
```

`checked.result.json` is the result file.
