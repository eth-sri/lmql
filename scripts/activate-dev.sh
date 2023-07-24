# use this script to run 'lmql' commands in the local development copy of LMQL
cd $(dirname $0)/.. > /dev/null
ABSOLUTE_LMQL_PATH=$(pwd)
cd - > /dev/null
echo "Using LMQL distribution in $ABSOLUTE_LMQL_PATH"
export PYTHONPATH=$ABSOLUTE_LMQL_PATH/src
alias lmql="PYTHONPATH=$ABSOLUTE_LMQL_PATH/src python -m lmql.cli \$*"
