# python-property-bag
A Python implementation of the "Property Bag" format from [Robert Nystrom's](https://journal.stuffwithstuff.com/) awesome C# Rogue-like [Amaranth](https://github.com/munificent/amaranth).


## Quick example
```python
import property_bag

s = """
:: abstract
    prop1 = 1

my class :: abstract
    prop2 = 2
"""

props = property_bag.loads(s)
```
