from lmql.tests.expr_test_utils import run_all_tests
from lmql.tests.queryargs.test_args import test_query_args
from lmql.tests.queryargs.test_var_errors import test_var_errors
from lmql.tests.queryargs.test_args_run import test_lmql_run_args
from lmql.tests.queryargs.test_args_query_str import test_query_args_with_str

run_all_tests(globals())