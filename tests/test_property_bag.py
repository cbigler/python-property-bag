from unittest import TestCase

from property_bag import PropertyBag


class TestPropertyBag(TestCase):
    def test_ctor_namevaluebase_throws_on_name_none(self):
        with self.assertRaises(ValueError):
            PropertyBag(None, 'bar', [PropertyBag('base')])

    def test_ctor_namevaluebase_throws_on_value_none(self):
        with self.assertRaises(ValueError):
            PropertyBag('foo', None, [PropertyBag('base')])

    def test_ctor_namevaluebase_does_not_throw_base_none(self):
        PropertyBag('foo', 'bar', None)

    def test_ctor_namevaluebase(self):
        prop = PropertyBag('foo', 'bar', [PropertyBag('base')])
        self.assertEqual('foo', prop.name)
        self.assertEqual('bar', prop.value)
        self.assertEqual(0, prop.count)

    def test_ctor_namevalue_throws_on_name_none(self):
        with self.assertRaises(ValueError) as ex:
            PropertyBag(None, 'bar')

    def test_ctor_namevalue_throws_on_value_none(self):
        with self.assertRaises(ValueError) as ex:
            PropertyBag('foo', None)

    def test_ctor_namevalue(self):
        prop = PropertyBag('foo', 'bar')
        self.assertEqual('foo', prop.name)
        self.assertEqual('bar', prop.value)
        self.assertEqual(0, prop.count)

    def test_ctor_name_throws_on_name_none(self):
        with self.assertRaises(ValueError) as ex:
            PropertyBag(None)

    def test_ctor_name(self):
        prop = PropertyBag('foo')
        self.assertEqual('foo', prop.name)
        self.assertEqual('', prop.value)
        self.assertEqual(0, prop.count)

    def test_string_indexer(self):
        prop = PropertyBag('foo')
        prop.add(PropertyBag('first', 'one'))
        prop.add(PropertyBag('second', 'two'))
        self.assertEqual('one', prop['first'].value)
        self.assertEqual('two', prop['second'].value)

    def test_string_indexer_returns_none_on_missing(self):
        prop = PropertyBag('foo')
        self.assertIsNone(prop['not found'])

    def test_add(self):
        prop = PropertyBag('foo', 'bar')
        self.assertEqual(0, prop.count)

        prop.add(PropertyBag('item', 'value'))

        self.assertEqual(1, prop.count)
        self.assertEqual('item', prop['item'].name)
        self.assertEqual('value', prop['item'].value)

    def test_contains(self):
        prop = PropertyBag('foo', 'bar')
        prop.add(PropertyBag('name', 'value'))

        self.assertTrue('name' in prop)
        self.assertFalse('not name' in prop)

    def test_get(self):
        prop = PropertyBag('foo', 'bar')
        found = PropertyBag('found', 'value')
        prop.add(found)

        # find one
        result = prop['found']
        self.assertEqual(result, found)

        # fail to find one
        result = prop['not found']
        self.assertIsNone(result)

    def test_get_or_default_string(self):
        prop = PropertyBag('foo', 'bar')
        prop.add(PropertyBag('name', 'value'))

        self.assertEqual('value', prop.get('name', 'default'))
        self.assertEqual('default', prop.get('not name', 'default'))

    def test_getint_or_default_int(self):
        prop = PropertyBag('foo', 'bar')
        prop.add(PropertyBag('name', '123'))

        self.assertEqual(123, prop.getint('name', 666))
        self.assertEqual(666, prop.getint('not name', 666))

    def test_get_converted(self):
        prop = PropertyBag('foo', 'bar')
        prop.add(PropertyBag('name', 'value'))

        def conv(s: str) -> str:
            return f'{s} (added)'

        self.assertEqual('value (added)', prop.convert('name', conv, 'default'))
        self.assertEqual('default', prop.convert('not name', conv, 'default'))

    def test_inherit_values_from_bases(self):
        base1_prop = PropertyBag('base1')
        base1_prop.add(PropertyBag('from base 1', 'value 1'))

        base2_prop = PropertyBag('base2')
        base2_prop.add(PropertyBag('from base 2', 'value 2'))

        derived_prop = PropertyBag('derived', '', (base1_prop, base2_prop))
        derived_prop.add(PropertyBag('from derived', 'value'))

        self.assertEqual(3, derived_prop.count)
        self.assertEqual('value 1', derived_prop['from base 1'].value)
        self.assertEqual('value 2', derived_prop['from base 2'].value)
        self.assertEqual('value', derived_prop['from derived'].value)

    def test_override_across_bases(self):
        base1_prop = PropertyBag('base1')
        base1_prop.add(PropertyBag('from base', 'value 1'))

        base2_prop = PropertyBag('base2')
        base2_prop.add(PropertyBag('from base', 'value 2'))

        derived_prop = PropertyBag('derived', '', (base1_prop, base2_prop))

        self.assertEqual(1, derived_prop.count)
        self.assertEqual('value 2', derived_prop['from base'].value)

    def test_override_value_from_base(self):
        base_prop = PropertyBag('base')
        base_prop.add(PropertyBag('from base', 'value'))
        base_prop.add(PropertyBag('override', 'base value'))

        derived_prop = PropertyBag('derived', '', (base_prop,))
        derived_prop.add(PropertyBag('from derived', 'value'))
        derived_prop.add(PropertyBag('override', 'derived value'))

        self.assertEqual(3, derived_prop.count)
        self.assertEqual('value', derived_prop['from base'].value)
        self.assertEqual('derived value', derived_prop['override'].value)
