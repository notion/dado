# dado
Data-driven test decorator

# What
Decorate a test to create indepenent tests for each decorated data set.

# Example

Given:
```python
from dado import data_driven

@data_driven(['first', 'second'], {
    'letters': ['a', 'b'],
    'numbers': [0, 1],
})
def test_first_two(first, second): ...
```

When you load the module, it will load as if you'd defined:
```python
def test_first_two_letters():
    return test_first_two('a', 'b')

def test_first_two_numbers():
    return test_first_two(0, 1)
```
