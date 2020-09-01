from __future__ import annotations

import logging
import regex
from typing import Iterable, List

logger = logging.getLogger(__name__)

INDENT_REGEX_PATTERN = r'^(?P<indent>\s*)(?P<text>.*)$'


class IndentationTree:
    """Given a collection of lines of text with leading whitespace used to indicate indentation,
    produces a tree of IndentationTree objects corresponding to the nesting of the text.
    """
    indent_regex = regex.compile(INDENT_REGEX_PATTERN)

    def __init__(self, indent: int, text: str) -> None:
        self._indent = indent
        self._text = text
        self._children = []

    def __str__(self):
        return self.build_string('', '')

    @property
    def indent(self) -> int:
        return self._indent

    @property
    def text(self) -> str:
        return self._text

    @property
    def children(self) -> Iterable[IndentationTree]:
        return self._children

    def normalize_indentation(self, current_indent: int) -> None:
        self._indent = current_indent
        for child in self._children:
            child.normalize_indentation(current_indent + 1)

    def build_string(self, sb: str, indent: str) -> str:
        if self._indent > -1:
            sb += indent
            sb += self._text
            indent += ''

        for child in self._children:
            sb += child.build_string(sb, indent)

        return sb

    @staticmethod
    def parse(lines: Iterable[str]) -> IndentationTree:
        if lines is None:
            raise ValueError('lines')

        stack: List[IndentationTree] = []
        root = IndentationTree(-1, '')
        stack.append(root)

        for line in lines:
            matches = IndentationTree.indent_regex.match(line)

            # create the new branch
            indent = len(matches['indent'])
            text = matches['text']
            logger.debug(f'Parsed line "{line}" -> "{text}" [{indent}]')
            tree = IndentationTree(indent, text)

            # find the right parent in the stack
            while stack[-1].indent >= indent:
                stack.pop()

            # the right parent should be at the top of the stack now
            logger.debug(f' -> Adding to "{stack[-1].text}"')
            stack[-1]._children.append(tree)
            stack.append(tree)

        root.normalize_indentation(-1)

        return root
