import lmql
from lmql.graphs.solvers import ExploreAll

from lmql.tests.expr_test_utils import run_all_tests

m = lmql.model("random", seed=123)

async def test_simple():
    @lmql.query(model=m)
    async def a():
        '''lmql
        return 'a'
        '''
    
    @lmql.query(model=m)
    async def b():
        '''lmql
        return 'b' + a()
        '''
    
    r = await b()
    assert r == "ba", "expected result 'ba', not '{}'".format(r)

async def test_ab_graph():
    @lmql.query(model=m)
    async def a():
        '''lmql
        return 'a'
        '''
    
    @lmql.query(model=m)
    async def b():
        '''lmql
        return 'b' + a()
        '''
    
    graph = await lmql.ainfer(b, samples=1)

    assert len(graph.nodes) == 2
    
    for n in graph.nodes:
        assert "a()" or "b" in n.name, "node must be one of a() or b, not '{}'".format(n.name)
        assert len(n.instances) == 1, "each node should have exactly one instance, but got {}".format(len(n.instances))
        if n.name == "a()":
            i = n.instances[0]
            assert i.result == "a", "expected result 'a' for a() node, but got {}".format(i.result)
        elif n.name == "b":
            i = n.instances[0]
            assert i.result == "ba", "expected result 'ba' for b node, but got {}".format(i.result)
    # assert r == "ba", "expected result 'ba', not '{}'".format(r)

async def test_simple_branch():
    @lmql.query(model=m)
    async def a():
        '''lmql
        return 'a'
        '''
    
    @lmql.query(model=m)
    async def b():
        '''lmql
        return 'b'
        '''
    
    @lmql.query(model=m)
    async def one():
        '''lmql
        r = a() | b()
        return "one of " + r
        '''
    
    # sample once
    graph = await lmql.ainfer(one, samples=1, solver=ExploreAll(early_stopping=False))

    assert len(graph.nodes) == 3

    assert_instance_values(instances(graph, "one"), ["one of a"])
    assert len(dangling_instances(graph, "one")) == 1
    assert_instance_values(instances(graph, "a()"), ["a"])
    assert len(dangling_instances(graph, "b()")) == 1

    # explore all
    graph = await lmql.ainfer(one, samples=2, solver=ExploreAll(early_stopping=False))

    assert len(graph.nodes) == 3

    assert_instance_values(instances(graph, "one"), ["one of a", "one of b"])
    assert len(dangling_instances(graph, "one")) == 0
    assert_instance_values(instances(graph, "a()"), ["a"])
    assert_instance_values(instances(graph, "b()"), ["b"])


async def test_simple_branch_3levels():
    @lmql.query(model=m)
    async def a_0():
        '''lmql
        return 'a'
        '''
    
    @lmql.query(model=m)
    async def a():
        '''lmql
        return a_0() + "both"
        '''

    @lmql.query(model=m)
    async def b0():
        '''lmql
        return 'b'
        '''

    @lmql.query(model=m)
    async def b():
        '''lmql
        return b0() + 'both'
        '''
    
    @lmql.query(model=m)
    async def one():
        '''lmql
        r = a() | b()
        return "one of " + r
        '''
    
    # sample once
    graph = await lmql.ainfer(one, samples=1, solver=ExploreAll(early_stopping=False))

    assert len(graph.nodes) == 5

    assert_instance_values(instances(graph, "one"), ["one of aboth"])
    assert len(dangling_instances(graph, "one")) == 1
    assert_instance_values(instances(graph, "a()"), ["aboth"])
    assert len(dangling_instances(graph, "b()")) == 1

    # explore all
    graph = await lmql.ainfer(one, samples=2, solver=ExploreAll(early_stopping=False))

    assert_instance_values(instances(graph, "one"), ["one of aboth", "one of bboth"])
    assert len(dangling_instances(graph, "one")) == 0
    assert_instance_values(instances(graph, "a()"), ["aboth"])
    assert_instance_values(instances(graph, "b()"), ["bboth"])

async def test_3levels_assertion_failure():
    ctr = 0

    @lmql.query(model=m)
    async def a_0():
        '''lmql
        return 'a'
        '''
    
    @lmql.query(model=m)
    async def a():
        '''lmql
        r = a_0()
        
        assert ctr > 1 
        
        return r + "both"
        '''

    @lmql.query(model=m)
    async def b0():
        '''lmql
        return 'b'
        '''

    @lmql.query(model=m)
    async def b():
        '''lmql
        return b0() + 'both'
        '''
    
    @lmql.query(model=m)
    async def one():
        '''lmql
        r = a() | b()
        return "one of " + r
        '''
    
    # sample once
    graph = await lmql.ainfer(one, samples=1, solver=ExploreAll(early_stopping=False))

    assert len(graph.nodes) == 5

    assert_instance_values(instances(graph, "one"), [])
    assert len(dangling_instances(graph, "one")) == 2
    # check for the retry node at a()
    assert_instance_values(dangling_instances(graph, "a()"), [None])
    assert_instance_values(instances(graph, "a()"), [])
    assert len(error_instances(graph, "a()")) == 1
    assert_instance_values(instances(graph, "a_0()"), ["a"])
    assert len(dangling_instances(graph, "b()")) == 1


def test_error_recovery():
    ctr = {'value': 1}

    @lmql.query(model=m)
    async def a_0():
        '''lmql
        return str(ctr['value'])
        '''

    @lmql.query(model=m)
    async def a():
        '''lmql
        r = a_0()
        
        try:
            assert ctr['value'] > 1
        finally:
            ctr['value'] += 1

        return r + 'both'
        '''

    @lmql.query(model=m)
    async def one(i=0):
        '''lmql
        return "one of " + a()
        '''

    graph = lmql.infer(one, samples=2)
    
    # makes sure that after two samples, the erroring node was retried successfully
    assert_instance_values(instances(graph, "one"), ["one of 2both"])

def dangling_instances(graph, node):
    node = [n for n in graph.nodes if n.name == node]
    assert len(node) == 1, "expected one query node for '{}', but got {}".format(node, len(node))
    return [i for i in node[0].instances if i.dangling and not i.error]

def error_instances(graph, node):
    node = [n for n in graph.nodes if n.name == node]
    assert len(node) == 1, "expected one query node for '{}', but got {}".format(node, len(node))
    return [i for i in node[0].instances if i.error is not None]

def instances(graph, node):
    node = [n for n in graph.nodes if n.name == node]
    assert len(node) == 1, "expected one query node for '{}', but got {}".format(node, len(node))
    return [i for i in node[0].instances if not i.dangling and not i.error]

def assert_instance_values(instance_list, value_list):
    assert len(instance_list) == len(value_list), "expected {} instances, but got {}".format(len(value_list), len(instance_list))

    values_of_instances = sorted([i.result for i in instance_list], key=lambda v: str(v))
    expected_values = sorted(value_list, key=lambda v: str(v))

    if not all(actual == expected for actual, expected in zip(values_of_instances, expected_values)):
        diff = "\n".join(f"{actual} {'=' if actual == expected else '!='} {expected}" for actual,expected in zip(values_of_instances, expected_values))
        
        assert False, "instance values do not match expected list:\nActual vs. Expected\n" + diff

if __name__ == "__main__":
    run_all_tests(globals())