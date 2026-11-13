"""
המחלקה Node: רשומת חיפוש אחת.
"""


class Node:
    """רשומת חיפוש: מצב, עלות ההגעה אליו, הערכת היתרה, והצומת הקודם במסלול."""

    __slots__ = ("state", "g", "h", "parent")

    def __init__(self, state, g, h, parent=None):
        self.state = state
        self.g = g
        self.h = h
        self.parent = parent

    @property
    def f(self):
        return self.g + self.h
