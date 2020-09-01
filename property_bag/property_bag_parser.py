import logging
import os
import regex
from pathlib import Path
from typing import Iterable, List

from .indentation_tree import IndentationTree
from .property_bag import PropertyBag

logger = logging.getLogger(__name__)


COMMENT_REGEX_PATTERN = r'''
    ^(?P<content>.*?)       # everything before the comment
    (?P<comment>//.*)?$     # the comment
'''

LINE_REGEX_PATTERN = r'''
    ^(?P<abstract>::)?              # may be abstract
    (?P<name>..*?)                  # name
    ((?P<equals>=)(?P<value>..*?)?  # '= value' (value may be omitted)
    |(::(?P<inherits>.*?))*         # or base props
    |                               # or nothing
    )$

'''

INCLUDE_REGEX_PATTERN = r'''
    ^\s*                    # allow white space before the include
    \#include               # the include command
    \s*                     # allow space after the include
    \"(?P<path>.*)\"        # the include path     
    $                               
'''

PropertyBagStack = List[PropertyBag]


class PropertyBagParser:
    comment_regex = regex.compile(COMMENT_REGEX_PATTERN, regex.VERBOSE)
    line_regex = regex.compile(LINE_REGEX_PATTERN, regex.VERBOSE)
    include_regex = regex.compile(INCLUDE_REGEX_PATTERN, regex.VERBOSE)

    @staticmethod
    def strip_empty_lines(lines: Iterable[str]) -> Iterable[str]:
        if lines is None:
            raise ValueError('lines')

        yield from filter(lambda l: len(l.strip()) > 0, lines)

    @staticmethod
    def _get_line_content(line) -> str:
        m = PropertyBagParser.line_regex.match(line)
        return m['content'] if m else ''

    @staticmethod
    def strip_comments(lines: Iterable[str]) -> Iterable[str]:
        if lines is None:
            raise ValueError('lines')

        yield from map(lambda l: PropertyBagParser.comment_regex.match(l)['content'], lines)

    @staticmethod
    def parse_includes(base_path: str, lines: Iterable[str]) -> Iterable[str]:
        if not base_path:
            raise ValueError('base_path')

        if not lines:
            ValueError('lines')

        logger.debug(f'Parsing includes using base "{base_path}"')
        for line in lines:
            matches = PropertyBagParser.include_regex.match(line)

            # if this isn't an include line, then just forward it and go to the next line
            if not matches:
                logger.debug(f'Ignoring non-include: {line}')
                yield line.rstrip()
                continue

            path = matches['path']
            logger.debug(f'Include found for {path}')
            full_path = f'{base_path}/{path}'

            if os.path.isdir(full_path):
                logger.debug(f'  Loading from directory "{full_path}')
                file_names = [f'{full_path}/{f}' for f in os.listdir(full_path) if os.path.isfile(f'{full_path}/{f}')]

                for file_name in file_names:
                    logger.debug(f'  Loading from file "{file_name}')
                    with open(file_name, 'r') as ifs:
                        lines = ifs.readlines()
                    yield from PropertyBagParser.parse_includes(path, lines)
            elif os.path.isfile(full_path):
                logger.debug(f'  Loading from file "{full_path}')
                with open(full_path, 'r') as ifs:
                    lines = ifs.readlines()
                yield from PropertyBagParser.parse_includes(base_path, lines)
            else:
                logger.error(f'Could not find include "{path}"')

    @staticmethod
    def parse(tree: IndentationTree) -> PropertyBag:
        if tree is None:
            raise ValueError('tree')

        root = PropertyBag('root', '')
        parents = [root]

        PropertyBagParser._parse_tree(tree, parents, [])

        return root

    @staticmethod
    def _parse_tree(tree: IndentationTree, parents: PropertyBagStack, abstract_props: PropertyBagStack) -> None:
        abstract_props.append(PropertyBag('abstract'))

        for child in tree.children:
            parent_prop = parents[-1]
            logger.debug(f'Parsing "{child.text}"')
            # parse the line
            matches = PropertyBagParser.line_regex.match(child.text)
            logger.debug(f'  matches "{matches}"')

            is_abstract = bool(matches['abstract'])
            logger.debug(f'  abstract={is_abstract}')

            name = matches['name'].strip() or str(parents[-1].count)
            logger.debug(f'  name={name}')

            inherits: List[str] = []
            for inherit in matches.captures('inherits'):
                inherit_name = inherit.strip()
                if not inherit_name:
                    inherit_name = name
                inherits.append(inherit_name)
            logger.debug(f'  inherits={inherits}')

            has_equals = bool(matches['equals'])
            logger.debug(f'  has_equals={has_equals}')

            if matches['value']:
                has_value = True
            else:
                has_value = False
            value = matches['value'].strip() if has_value else ''
            logger.debug(f'  has_value={has_value}')

            if has_equals and has_value:
                # fully specified text property
                parent_prop.add(PropertyBag(name, value))
                # ignore any children
            elif has_equals:
                # beginning of a multi-line text property
                for text_child in child.children:
                    # separate lines with a space
                    if value:
                        value += ' '
                    value += text_child.text
                parent_prop.add(PropertyBag(name, value))
            else:
                # collection property

                # look up bases from this property's prior siblings
                bases: List[PropertyBag] = []
                for base_name in inherits:
                    base_prop = None

                    # walk up the concrete property stack
                    for parent in parents[::-1]:
                        if base_name in parent:
                            base_prop = parent[base_name]
                            break

                    # if we didn't find a concrete one, look for an abstract one
                    if not base_prop:
                        logger.debug(f'Searching for abstract prop "{base_name}"')
                        for prop in abstract_props[::-1]:
                            logger.debug(f'  checking {prop}')
                            if base_name in prop:
                                base_prop = prop[base_name]
                                break

                    if base_prop:
                        bases.append(base_prop)
                    else:
                        logger.warning(f'Could not find base "{base_name}" for prop "{name}"')

                prop = PropertyBag(name, '', bases)
                logger.debug(f'  Parsed new collection prop bag: {name} {[str(b) for b in bases]}')

                # add it to the appropriate group
                if is_abstract:
                    abstract_props[-1].add(prop)
                else:
                    parent_prop.add(prop)

                # recurse
                parents.append(prop)
                PropertyBagParser._parse_tree(child, parents, abstract_props)

        parents.pop()
        abstract_props.pop()

    @staticmethod
    def from_file(file_path: str) -> PropertyBag:
        path = Path(file_path)
        with open(file_path, 'r') as ifs:
            lines = ifs.readlines()

        included = PropertyBagParser.parse_includes(path.parent, lines)
        no_comments = PropertyBagParser.strip_comments(included)
        no_whitespace = PropertyBagParser.strip_empty_lines(no_comments)

        tree = IndentationTree.parse(no_whitespace)
        return PropertyBagParser.parse(tree)

