from munch import Munch
from tf.app import use
import pandas as pd

B = use("etcbc/dss", hoist=globals())
DSS = Munch({"F": F, "L": L, "T": T, "name": "DSS", "A": B})

A = use("etcbc/bhsa", hoist=globals())
BHSA = Munch({"F": F, "L": L, "T": T, "name": "BHSA", "A": A})

del F, L, T

import os
import collections
from itertools import chain
from collections import defaultdict

dss_sections = {}
for word in DSS.F.otype.s("word"):
    scroll = DSS.T.scrollName(DSS.L.u(word, "scroll")[0])
    book = DSS.F.book_etcbc.v(word)
    chapter = DSS.F.chapter.v(word)
    verse = DSS.F.verse.v(word)
    if None in (scroll, book, chapter, verse):
        continue
    section = (book, chapter, verse)
    dss_sections.setdefault(section, {}).setdefault(scroll, []).append(word)


def remove_duplicates(iterable):
    return list(dict.fromkeys(iterable))


def remove_duplicates(iterable):
    return list(dict.fromkeys(iterable))


class TFOb:
    def __init__(self, ids, source):
        if type(ids) is int:
            ids = [ids]
        self.ids = remove_duplicates(ids)
        self.source = source
        self._levels = ["to_" + otype + "s" for otype in source.F.otype.all]

    @classmethod
    def all(self, level, source):
        return TFOb(list(source.F.otype.s(level)), source)

    @classmethod
    def section(self, section, source, scroll=None):
        if source.name == "BHSA":
            return TFOb(source.T.nodeFromSection(section), source)

        section = (section[0], str(section[1]), str(section[2]))
        dss_section = dss_sections[section]
        if scroll is None:
            scroll = list(dss_section.keys())[0]
        return TFOb(dss_section[scroll], source)

    def __getattr__(self, attr):
        if attr in self._levels:
            level = "to_" + self.level + "s"
            if self.level == "none":
                return self
            level_index = self._levels.index(level)
            new_level_index = self._levels.index(attr)
            if new_level_index > level_index:
                return self.down(attr[3:-1])
            elif new_level_index < level_index:
                return self.up(attr[3:-1])
            else:
                return self

        if self.source.name == "DSS" and attr == "lex":
            attr = "lex_etcbc"

        feature = getattr(self.source.F, attr)
        return [getattr(self.source.F, attr).v(id_) for id_ in self.ids]

    def copy(self):
        return TFOb(self.ids.copy(), source)

    def up(self, otype=None):
        if self.level in (otype, "none"):
            return self
        return TFOb(
            chain(*[self.source.L.u(id_, otype) for id_ in self.ids]),
            source=self.source,
        )

    def down(self, otype=None):
        if self.level in (otype, "none"):
            return self
        return TFOb(
            chain(*[self.source.L.d(id_, otype) for id_ in self.ids]),
            source=self.source,
        )

    def filter(self, **kwargs):
        ids = []
        for id_ in self.ids:
            for key, value in kwargs.items():
                if key == "lex" and self.source.name == "DSS":
                    key = "lex_etcbc"
                if getattr(self.source.F, key).v(id_) != value:
                    break
            else:
                ids.append(id_)
        return TFOb(ids, source=self.source)

    def filter_in(self, **kwargs):
        for key in kwargs:
            kwargs[key] = set(kwargs[key])
        ids = []
        for id_ in self.ids:
            for key, values in kwargs.items():
                if key == "lex" and self.source.name == "DSS":
                    key = "lex_etcbc"
                if getattr(self.source.F, key).v(id_) not in values:
                    break
            else:
                ids.append(id_)
        return TFOb(ids, source=self.source)

    def first(self, **kwargs):
        ids = []
        for id_ in self.ids:
            for key, value in kwargs.items():
                if key == "lex" and self.source.name == "DSS":
                    key = "lex_etcbc"
                if getattr(self.source.F, key).v(id_) != value:
                    break
            else:
                return TFOb(id_, source=self.source)
        return TFOb([], source=self.source)

    def __getitem__(self, i):
        return TFOb(self.ids[i], source=self.source)

    def __len__(self):
        return len(self.ids)

    @property
    def text(self):
        return self.source.T.text(self.ids)

    def str(self, word_limit=None):
        if self.level not in ("word", "none"):
            return self.to_words.str(word_limit)
        if word_limit is not None and len(self) > word_limit:
            return self[: word_limit // 2].str() + " [...] " + self[-word_limit // 2 :].str()
        else:
            return " ".join([g_cons for g_cons in self.g_cons if g_cons])

    def __str__(self):
        return self.str()

    def __dir__(self):
        return list(self.__dict__.keys()) + dir(self.source.F) + self._levels

    def __add__(self, ob):
        return TFOb(self.ids + ob.ids, source=self.source)

    @property
    def level(self):
        if len(self.ids) > 0:
            return self.otype[0]
        return "none"

    def pretty(self, extraFeatures=("sp", "function")):
        if len(self) == 0:
            return
        levels = self.source.F.otype.all
        ob = self
        level_index = levels.index(ob.level)
        while len(ob) != 1:
            level_index -= 1
            ob = self.up(levels[level_index])
        self.source.A.pretty(ob.ids[0], extraFeatures=extraFeatures)

    def __repr__(self):
        level = self.level
        if level != "none":
            level += "s"

        return f'<{self.level}_{len(self)} "{self.str(40)}">'

    def _get_sections(self):
        if self.source.name == "DSS":
            return list(
                zip(
                    self.__getattr__("book_etcbc"),
                    self.__getattr__("chapter"),
                    self.__getattr__("verse"),
                )
            )
        elif self.source.name == "BHSA":
            return [self.source.T.sectionFromNode(id_) for id_ in self.ids]

    @property
    def book(self):
        return [section[0] for section in self._get_sections()]

    @property
    def chapter(self):
        return [section[1] for section in self._get_sections()]

    @property
    def verse(self):
        return [section[2] for section in self._get_sections()]
