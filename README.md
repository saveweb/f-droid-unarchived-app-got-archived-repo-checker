# f-droid-unarchived-app-got-archived-repo-checker

## Usage

```bash
rm checked.result.json -f # remove result files
git clone --depth=1 https://gitlab.com/fdroid/fdroiddata.git # clone fdroid metadata repository
```

```bash
python -m archived_repo_checker.fdroid ./fdroiddata/metadata # run checker, this action is resumable (Ctrl+C to stop, and run again to continue)
```

`checked.result.json` is the result file.
