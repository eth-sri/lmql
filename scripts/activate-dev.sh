# use this script to run 'lmql' commands in the local development copy of LMQL
ABSOLUTE_LMQL_PATH=$(cd $(dirname $0)/.. && pwd)
echo "Using LMQL distribution in $ABSOLUTE_LMQL_PATH"
export PYTHONPATH=$ABSOLUTE_LMQL_PATH/src
alias lmql="PYTHONPATH=$ABSOLUTE_LMQL_PATH/src python -m lmql.cli \$*"
