# Development


## Create a new distribution

### Checklist before creating a new distribution

Before creating a new distribution, the following checklist should be completed:

- [ ] Double check the version number in `pyproject.toml`.
- [ ] Run the test suite: `pytest -v` (all tests must pass).
- [ ] Remove the `dist` folder, the EGG-INFO folder, and the `build` folder.
- [ ] Remove the conda environment and create a new one (`conda remove -n pydg_analysis --all`)
- [ ] Install new conda environment (`conda create -n pydg_analysis python=3.11`)


1. Update the version number in `pyproject.toml` and `default_configs.toml`.
2. Create a new distribution with the following command:

```bash
pip install build
```

If used in development mode, the following command is necessary (in the root directory of the repository):

```bash
pip install --editable .
```

**DO NOT MAKE THE FINAL TESTS IN DEVELOPMENT MODE!**

Otherwise, create the tar.gz and wheel files with the following command:

```bash
python -m build
```


## Checklist

After creating a new distribution, the following checklist should be completed:

- [ ] Double check the version number in `pyproject.toml`.
- [ ] Run the test suite: `pytest -v`
- [ ] Check if the package is importable with the following command:
  - [ ] `python -c "import pynamicgain"`
  - [ ] python -> `import pynamicgain as pydg` -> `pydg.__version__`
- [ ] Check if the package is locally installable: `pip install dist/PynamicGain-<version>-py3-none-any.whl`
- [ ] Run all major commands
  - [ ] `pydg_help`
  - [ ] `pydg_new_setup`
  - [ ] `pydg_backup_csv`



## Documentation

Install additional dependencies with the following command:

```bash
pip install .[docs]
```

Add the pyreverse class and package overviews:

```bash
pyreverse pynamicgain
```

Transform the dot files to png files:

```bash
dot -Tpng packages.dot > docs/source/explanations/_images/pynamicgain_package.svg -Gdpi=300
dot -Tpng classes.dot > docs/source/explanations/_images/pynamicgain_classgraph.svg -Gdpi=300
```

Delete the dot files:

```bash
rm packages.dot classes.dot
```

To build the documentation, use the following command:

```bash
sphinx-apidoc -f -o docs/source/_apidoc/ pynamicgain
sphinx-build -b html docs/source docs/_build/html
```

This will currently generate 5 warnings, which are not critical.


## Testing

PynamicGain ships with a pytest-based test suite.  Install the test
dependencies and run:

```bash
pip install -e ".[test]"
pytest -v
```

To skip the Numba JIT compilation tests (faster iteration):

```bash
pytest -v -m "not slow"
```

To see a coverage report:

```bash
pytest --cov=pynamicgain --cov-report=term-missing
```

Tests are also executed automatically on every push and pull request via
GitHub Actions (`.github/workflows/tests.yml`).


## Outlook/TODO

- [ ] Finish the documentation
- [ ] Change Image Composition in the mini spike train analysis
- [ ] Add phase plot to the analysis
- [ ] Add DG analysis option (online/offline)
- [ ] Add whole folder analysis option
