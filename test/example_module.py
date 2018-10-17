import dado


@dado.data_driven(
    ('foo', 'bar'),
    {
        'one_two': (1, 2),
        'a_b': ('a', 'b'),
    }
)
def func(foo, bar):
    return foo, bar
