# Contributing

Thank you so much for your interest in contributing to LMQL, we are very happy to have you here! We 
actively encourage any form of contribution, and are convinced that LMQL should be a community-driven
project.

## Pull Request Process

1. **Reach Out** If you are planning to implement a new feature (not just a bugfix), please open an issue first or come and talk to the team in our [community Discord](https://discord.gg/7eJP4fcyNT) (#dev channel). In general we are very open to new and 
   experimental ideas, but we want to make sure that the feature is in line with the overall goals of the project and that it is not already being worked on.
2. **Test Well** Please make sure that your code is well-tested. For this also see the 'Testing' section below.
3. **Import Defensively** Please make sure your code uses defensive imports, i.e. imports that do not fail if a dependency is not installed. For example, if you are using the `transformers` library, you should use `try/except` blocks to catch the `ModuleNotFoundError` that is raised if the library is not installed. This is  important because we want to make sure that LMQL can be installed without all dependencies, and that the user is only required to install the dependencies that are actually needed for their use case.
4. **Document Your Changes** If your contributions or feature requires new forms of configuration or syntax, please make sure to also provide a documentation chapter for it. You can find the MarkDown-based documentation in the `docs/` directory. A script for building and previewing the documentation is provided in `scripts/serve-all.py` (also serves the website and browser playground).

## Testing

**General Testing** For general testing, please make sure that your code is compatible with multiple backends, e.g. if possible try to test with `transformers` models, OpenAI models and `llama.cpp`. LMQL is designed as a vendor-agnostic language, which means all features should be available across all backends. If you do not have the hardware to test changes with multiple backends, please make sure to ask a team member to run the tests for you, before merging your pull request.

**Dependency Changes/Updates** After adding new dependencies, `scripts/flake.d/poetry.lock` needs to be updated. This can be done by running `(cd scripts/flake.d && exec poetry lock --no-update)` (if you run Nix, `nix develop .#minimal` will put you in a shell with the `poetry` command available, even if the `poetry.lock`, `pyproject.cfg`, and other related files are currently broken). If you are able, please also check that the Nix build works after making dependency changes; if you're not in a position to do this, please feel encouraged to request a hand on Discord.

**Running Test Suites** The repository contains a number of test suites in the `src/lmql/tests/` directory. To run all 
tests simply run `python src/lmql/tests/all.py`. Note that for some tests you need to configure an
OpenAI API key according to the instructions in [documentation](https://lmql.ai/docs/en/stable/language/openai.html).
We are working to remove the external dependency on the OpenAI API, but for now it is still required
for some tests. If you cannot get an API key, you can ask one of the core maintainers to run the
tests for your, once your pull request is ready.

**Adding Tests** You are also invited to add new tests in the form of a new `test_*.py` file in the `src/lmql/tests/` 
directory. For an example of how to write tests, please see the e.g. `https://github.com/eth-sri/lmql/blob/main/src/lmql/tests/test_functions.py`.
As demonstrated by this file, also try to implement your tests using `lmql.model("random", seed=<SEED>)` to make sure
your test code can be run without actually using an LLM or external API, and that it can be re-run
deterministically.

**[Optional] Web Build Testing:** If you are working on a feature that is available in the web playground of LMQL (e.g. also works with API-based (OpenAI) models only), you can also test the web build with `scripts/serve-all.py`, by typing `bb` for browser build into the script's prompt. This will build and serve the WebAssembly/Pyodide version of LMQL on `http://localhost:8081/playground/`. Please see `scripts/deploy-web.sh` for the build process and requirements of the web playground, which may require you to install additional dependencies. 

## Licensing

By contributing to LMQL you agree to license your contributions under the terms of
the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) as included in the [LICENSE](./LICENSE) file.

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as
contributors and maintainers pledge to making participation in our project and
our community a harassment-free experience for everyone, regardless of age, body
size, disability, ethnicity, gender identity and expression, level of experience,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment
include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery and unwelcome sexual attention or
advances
* Trolling, insulting/derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or electronic
  address, without explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

### Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable
behavior and are expected to take appropriate and fair corrective action in
response to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or
reject comments, commits, code, wiki edits, issues, and other contributions
that are not aligned to this Code of Conduct, or to ban temporarily or
permanently any contributor for other behaviors that they deem inappropriate,
threatening, offensive, or harmful.

### Scope

This Code of Conduct applies both within project spaces and in public spaces
when an individual is representing the project or its community. Examples of
representing a project or community include using an official project e-mail
address, posting via an official social media account, or acting as an appointed
representative at an online or offline event. Representation of a project may be
further defined and clarified by project maintainers.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported by contacting the project team at [hello@lmql.ai](mailto:hello@lmql.ai). All
complaints will be reviewed and investigated and will result in a response that
is deemed necessary and appropriate to the circumstances. The project team is
obligated to maintain confidentiality with regard to the reporter of an incident.
Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good
faith may face temporary or permanent repercussions as determined by other
members of the project's leadership.

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4,
available at [http://contributor-covenant.org/version/1/4][version]

[homepage]: http://contributor-covenant.org
[version]: http://contributor-covenant.org/version/1/4/
