"""Testing dependency graphs"""
import random
import sys

if not sys.version_info < (2, 7):
    from hypothesis import strategies as st
    from hypothesis import given

from . import Command, FunctionCommand, test

if sys.version_info < (2, 7):
    import mock
    given = mock.MagicMock()  # noqa
    example = mock.MagicMock()  # noqa
    st = mock.MagicMock()  # noqa

RES_COUNT = 35

range_intagers_st = st.integers(min_value=0, max_value=RES_COUNT)


@st.composite
def provide_require_st(draw, filter_=True):
    commands = draw(range_intagers_st)
    provides = draw(
        st.lists(
            st.lists(range_intagers_st),
            min_size = commands,
            max_size = commands
        )
    )
    is_func = draw(
        st.lists(
            st.booleans(),
            min_size = commands,
            max_size = commands
        )
    )
    provides_set = set()
    for command in provides:
        provides_set.update(command)
    requires = []
    if provides_set:
        for command in provides:
            if command:
                max_prov = max(command)
            else:
                max_prov = 0
            if filter_:
                provides_filter = [x for x in provides_set if x > max_prov]
            else:
                provides_filter = provides_set
            if provides_filter:
                sample = st.sampled_from(provides_filter)
                requires.append(draw(st.lists(sample)))
            else:
                requires.append([])
    else:
        requires = [[]] * commands
    return (provides, requires, is_func)


def print_example():
    example = provide_require_st().example()
    print("""
    digraph g {
         label="Command graph";
         graph [splines=line];
    """)
    for i in range(len(example[0])):
        print("    c%03d [shape=triangle];" % i)
        for provides in example[0][i]:
            print("    c%03d -> r%03d;" % (i, provides))
        for requires in example[1][i]:
            print("    r%03d -> c%03d;" % (requires, i))

    print("}")


@test.hypothesis_min_ver
@given(provide_require_st(), st.random_module())
def test_graph_basic(tree, rnd):
    """Test our test method, create a basic graph using hypthesis and run some
    basic tests against it."""
    run_graph(tree)


@test.hypothesis_min_ver
@given(provide_require_st(False), st.random_module())
def test_graph_cycles(tree, rnd):
    """Test reacts correctly on trees with cycles."""
    try:
        run_graph(tree)
    except ValueError as e:
        if "Commands with unresolved deps" not in e.args[0]:
            raise e


@test.hypothesis_min_ver
@given(
    provide_require_st(),
    provide_require_st(),
    st.random_module()
)
def test_graph_island(tree0, tree1, rnd):
    """Test with two independant graphs which can form a island"""
    tree = (tree0[0] + tree1[0], tree0[1] + tree1[1], tree0[2] + tree1[2])
    run_graph(tree)


def run_graph(tree):
    """Runs the test"""
    commands = []
    index = list(range(len(tree[0])))
    random.shuffle(index)
    for i in index:
        def dummy():
            return i

        if tree[2][i]:
            cmd = FunctionCommand(dummy)
        else:
            cmd = Command(i)
        for provides in tree[0][i]:
            cmd.provide("virtual", provides)
        for requires in tree[1][i]:
            cmd.require("virtual", requires)
        commands.append(cmd)
    ordered = Command.order_commands(commands)
    assert len(commands) == len(ordered)
    provided = set()
    for command in ordered:
        assert command._requires.issubset(provided)
        provided.update(command._provides)
