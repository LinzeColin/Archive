# Archive

Archived and reference project hub for LinzeColin.

This repository is a parent index that keeps archived/reference repositories
together as git submodules. The original repositories remain independent and
keep their own history, issues, settings, and release flow.

## Projects

| Path | Repository |
| --- | --- |
| `COM1005` | https://github.com/LinzeColin/COM1005 |
| `Linear-Regression-Live-Series` | https://github.com/LinzeColin/Linear-Regression-Live-Series |

## Clone

```bash
git clone --recurse-submodules git@github.com:LinzeColin/Archive.git
```

If already cloned:

```bash
git submodule update --init --recursive
```

## Update submodule pointers

```bash
git submodule update --remote --merge
git status
git add .gitmodules COM1005 Linear-Regression-Live-Series
git commit -m "Update archive submodule pointers"
git push
```

## Rule

Do not move project source code into this parent repository unless a future
monorepo migration is explicitly approved. This parent repository should remain
a clean navigation and orchestration layer.
