# Documentation

<div class="subtitle">Learn how to extend the LMQL documentation.</div>

LMQL's documentation ships as part of the main repository in the `docs/` folder. Most chapters are written in Markdown, with some pages provided as Jupyter Notebook. The documentation also includes the project website, including feature demonstrations and example code as showcased on the landing page.

## Chapters

* **Language** - Resources and documenation for the LMQL core language and its capabilities. With the exception of the [language reference](../language/reference.md), this part of the documentation is written in a "guide"-style, demonstrating LMQL's practical features using examples.

* **Model Support** - This part of the documentation provides an overview of the different model backends supported by LMQL, as well as instructions on how to integrate them into your workflow.

* **Library** - This part of the documentation provides an overview of the LMQL standard library. On the one hand, this includes forms of integrating LMQL in Python, on the hand, this includes the standard library of LMQL itself (e.g. Chat, Output, Actions, etc.).

* **Development** - This part of the documentation provides information on how to extend LMQL, how to contribute to the project, and how to setup a development environment.

## Building the documentation

The documentation build for the website uses [Vitepress](https://vitepress.dev) and is automatically built and deployed using GitHub Actions. To build the documentation locally, you can use the following commands:

```bash
# enter docs/ directory
cd docs
# install dependencies
yarn 
# run hot-reloading live server
yarn docs:dev
```