from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from unittest import TestCase

from property_bag.indentation_tree import IndentationTree
from property_bag.property_bag_parser import PropertyBagParser, PropertyBag


logging.basicConfig(level=logging.DEBUG)


class PropAsserter:
    def __init__(self, name: str, value: str, base_names: str = '', children: List[PropAsserter] = None) -> None:
        if not isinstance(base_names, str):
            raise ValueError('base_names')

        self._name = name
        self._value = value
        self._base_names = base_names
        self._children: List[PropAsserter] = children or []

    def test(self, prop: PropertyBag) -> None:
        if self._name != prop.name:
            raise AssertionError('Names are not equal')

        if self._value != prop.value:
            raise AssertionError('Values are not equal')

        if self._base_names:
            bases = self._base_names.split(',')
            num_bases_expected = len(bases)
            num_bases_found = len(prop.bases)
            if num_bases_expected != num_bases_found:
                raise AssertionError(f'Property "{prop.name}" does not inherit the expected number of bases; expected {num_bases_expected} "{bases}", found {num_bases_found} "{prop.bases}".')

            for i in range(0, len(bases)):
                if bases[i] != prop.bases[i].name:
                    raise AssertionError(
                        f'Property "{prop.name}" does not inherit the expected bases "{self._base_names}".')

            if len(self._children) != prop.count:
                raise AssertionError(f'Property "{prop.name}" does not have the expected number of children: {len(self._children)}')

        for child in self._children:
            if child._name not in prop:
                raise AssertionError(f'Property "{prop.name}" does not have the expected key "{child._name}"')

            child.test(prop[child._name])


class TestPropertyBagParser(TestCase):
    temp_dir = None

    def parse_includes(self, lines):
        return list(PropertyBagParser.parse_includes(self.temp_dir.name, lines))

    @staticmethod
    def assert_prop(prop, name, value, base_names, children):
        asserter = PropAsserter(name, value, base_names, children)
        asserter.test(prop)

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = TemporaryDirectory()
        temp_dir_name = Path(cls.temp_dir.name)

        with temp_dir_name.joinpath('include.txt').open("w") as ofs:
            ofs.write('\n'.join(('included text', f'#include "nested.txt"')))

        with temp_dir_name.joinpath('nested.txt').open("w") as ofs:
            ofs.write('nested line\n')

        subdir = temp_dir_name.joinpath('sub')
        subdir.mkdir()

        with subdir.joinpath('a.txt').open('w') as ofs:
            ofs.write('a\n')

        with subdir.joinpath('b.txt').open('w') as ofs:
            ofs.write('b\n')

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.temp_dir:
            cls.temp_dir.cleanup()

    def test_strip_empty_lines_raise_on_none(self):
        PropertyBagParser.strip_empty_lines(None)

    def test_strip_empty_lines_no_lines(self):
        result = list(PropertyBagParser.strip_empty_lines([]))
        self.assertEqual(0, len(result))

    def test_strip_empty_lines(self):
        lines = [
            '',
            'a',
            ' ',
            'b',
            '  c',
            '      ',
            'd',
            '',
            'e',
            ' '
        ]

        results = list(PropertyBagParser.strip_empty_lines(lines))

        self.assertEqual(5, len(results))
        self.assertEqual('a', results[0])
        self.assertEqual('b', results[1])
        self.assertEqual('  c', results[2])
        self.assertEqual('d', results[3])
        self.assertEqual('e', results[4])

    def test_strip_comments(self):
        lines = [
            'no comments',
            '',             # empty line
            '  ',           # whitespace only
            '// comment at start of line',
            '  // comment after whitespace',
            ' // comment with // other comment',
            'stuff before // comment',
            'stuff before // comment // with comment',
            'single / slash',
            'single / slash and // comment'
        ]

        results = list(PropertyBagParser.strip_comments(lines))

        self.assertEqual(len(lines), len(results))
        self.assertEqual('no comments',             results[0])
        self.assertEqual('',                        results[1])
        self.assertEqual('  ',                      results[2])
        self.assertEqual('',                        results[3])
        self.assertEqual('  ',                      results[4])
        self.assertEqual(' ',                       results[5])
        self.assertEqual('stuff before ',           results[6])
        self.assertEqual('stuff before ',           results[7])
        self.assertEqual('single / slash',          results[8])
        self.assertEqual('single / slash and ',     results[9])

    def test_parseincludes_raise_on_base_path_none(self):
        with self.assertRaises(ValueError):
            list(PropertyBagParser.parse_includes(None, []))

    def test_parseincludes_raise_on_lines_none(self):
        with self.assertRaises(ValueError):
            list(PropertyBagParser.parse_includes('', None))

    def test_parseincludes_includefile(self):
        lines = self.parse_includes([
            'before',
            '#include "include.txt"',
            "after"
        ])

        self.assertEqual(4, len(lines))
        self.assertEqual('before', lines[0])
        self.assertEqual('included text', lines[1])
        self.assertEqual('nested line', lines[2])
        self.assertEqual('after', lines[3])

    def test_parseincludes_missingfile(self):
        lines = self.parse_includes([
            'before',
            '#include "missing.txt"',
            "after"
        ])

        self.assertEqual(2, len(lines))
        self.assertEqual('before', lines[0])
        self.assertEqual('after', lines[1])

    def test_parse_raises_on_none(self):
        with self.assertRaises(ValueError):
            PropertyBagParser.parse(None)

    def test_parse_simple(self):
        tree = IndentationTree.parse(["simple name = simple value"])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('simple name', 'simple value')
        ])

    def test_parse_odd_characters(self):
        tree = IndentationTree.parse(['!@#$%^&*-_+[]\\|{};:\'",<.>/? = !@#$%^&*-=_+[]\\|{};:\'",<.>/?'])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('!@#$%^&*-_+[]\\|{};:\'",<.>/?', '!@#$%^&*-=_+[]\\|{};:\'",<.>/?')
        ])

    def test_parse_multiline(self):
        tree = IndentationTree.parse([
            'multi-line =',
            '  first',
            '  second',
            '  third',
            'nest',
            '   multi-line =',
            '       first',
            '       second',
            '       third',
        ])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('multi-line', 'first second third'),
            PropAsserter('nest', '', '', [
                PropAsserter('multi-line', 'first second third')
            ])
        ])

    def test_parse_nested(self):
        tree = IndentationTree.parse([
            "parent",
            "  child1 = 1",
            "  child2",
            "    grandchild1 = blah",
            "    grandchild2 = blah",
            "  child3",
        ])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('parent', '', '', [
                PropAsserter('child1', '1'),
                PropAsserter('child2', '', '', [
                    PropAsserter('grandchild1', 'blah'),
                    PropAsserter('grandchild2', 'blah'),
                ]),
                PropAsserter('child3', '')
            ])
        ])

    def test_parse_trimmed_whitespace(self):
        tree = IndentationTree.parse([
            "whitespace after    =    and before  ",
        ])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('whitespace after', 'and before')
        ])

    def test_parse_inherits(self):
        tree = IndentationTree.parse([
            'base',
            'derive with same name',
            ':: abstract base',
            'derived :: base',
            '  child base :: base',
            '  other child :: child base',
            '  derive with same name ::',
            'other derived :: abstract base',
        ])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('base', ''),
            PropAsserter('derive with same name', ''),
            PropAsserter('derived', '', 'base', [
                PropAsserter('child base', '', 'base'),
                PropAsserter('other child', '', 'child base'),
                PropAsserter('derive with same name', '', 'derive with same name')
            ]),
            PropAsserter('other derived', '', 'abstract base')
        ])

    def test_parse_inherit_with_same_name_does_not_reuse_self(self):
        tree = IndentationTree.parse([
            'foo',
            '  bar = in base',
            'a',
            '  foo ::',
            '    bar = overridden',
            'b',
            '  foo ::',
        ])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('foo', '', '', [
                PropAsserter('bar', 'in base')
            ]),
            PropAsserter('a', '', '', [
                PropAsserter('foo', '', '', [
                    PropAsserter('bar', 'overridden')
                ])
            ]),
            PropAsserter('b', '', '', [
                PropAsserter('foo', '', '', [
                    PropAsserter('bar', 'in base')
                ])
            ]),
        ])

    def test_parse_multiple_inheritence(self):
        tree = IndentationTree.parse([
            ':: a',
            '  foo = from a',
            '  bar = from a',
            ':: b',
            '  foo = from b',
            '  baz = from b',
            'c :: a :: b',
            '  sprang = from c'
        ])

        prop = PropertyBagParser.parse(tree)

        self.assert_prop(prop, '', '', '', [
            PropAsserter('c', '', 'a,b', [
                PropAsserter('foo', 'from b'),
                PropAsserter('bar', 'from a'),
                PropAsserter('baz', 'from b'),
                PropAsserter('sprang', 'from c'),
            ])
        ])
