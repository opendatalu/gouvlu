# gouvlu

Official udata theme of the Open Data Portal of Luxembourg

## Usage

Install the theme package in you udata environement:

```bash
pip install gouvlu
```

Then, define the installed theme as current in you `udata.cfg`:

```python
THEME = 'gouvlu'
```

## Development

There is a `docker-compose` configuration to get started fast.
Just run:

```bash
docker-compose up
```

Then go to <http://localhost:7000> to connect to the development server
with live reload.

### Local setup

If you want to execute some development tasks like extracting the translations or running the test suite, you need to install the dependencies localy (in a virtualenv).

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements/develop.pip
```

If you want to build assets, you also need node.js. The prefered way is with [nvm][]:

```bash
nvm use
npm install
inv assets_build
```

Ok, you are ready, you can now execute some Development commands.

```bash
inv -l
Available tasks:

  all            Run tests, reports and packaging
  assets-build   Build static assets
  assets-watch   Build assets on change
  clean          Cleanup all build artifacts
  cover          Run tests suite with coverage
  dist           Package for distribution
  i18n           Extract translatable strings
  i18nc          Compile translations
  pydist         Perform python packaging (without compiling assets)
  qa             Run a quality report
  test           Run tests suite
```

Let's execute an entire build:

```bash
inv
```

## Releasing

`gouvlu` uses [bumpr][] to perform release.
Simply execute:

```bash
# Install bumpr if not already installed
pip install bumpr
# Dry run to preview changes
bumpr -dv
# Perform release
bumpr
```
Bumpr will execute test, package everything, update changelog, handle tagging and push to upstream repository...
You just have to wait for the build to succeed and your release is available.

[nvm]: https://github.com/creationix/nvm#readme
[bumpr]: https://bumpr.readthedocs.io/
