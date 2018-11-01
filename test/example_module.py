"""Example Module for testing Dado."""


# [ Imports:Project ]
import dado


@dado.data_driven(
    ('foo', 'bar'),
    {
        'one_two': (1, 2),
        'a_b': ('a', 'b'),
    },
)
def func(foo, bar):
    """Return the args."""
    return foo, bar
