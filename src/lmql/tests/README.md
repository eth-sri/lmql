# Testing

**Running Test Suites** The directory contains a number of test suites. To run all tests, execute `python src/lmql/tests/all.py`. Note that for some tests you need to configure an OpenAI API key according to the instructions in documentation. We are working to remove the external dependency on the OpenAI API, but for now it is still required for some tests.

**Adding Tests** You are also invited to add new tests in the form of a new `test_*.py` file in the `src/lmql/tests/` directory. For an example of how to write tests, please see the e.g. https://github.com/eth-sri/lmql/blob/main/src/lmql/tests/test_nested_queries.py. As demonstrated by this file, also try to implement your tests using lmql.model("random", seed=<SEED>) to make sure your test code can be run without actually using an LLM or external API, and that it can be re-run deterministically.
