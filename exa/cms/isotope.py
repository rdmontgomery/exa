# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016, Exa Analytics Development Team
# Distributed under the terms of the Apache License 2.0
"""
Table of Isotopes
###########################################
This module provides an interface for interacting with isotopes of atoms; the
extended periodic table. For convenience, functions are provided for obtaining
traditionally used elements. This module also provides mappers for commonly
used dataframe manipulations.
"""
import six
import pandas as pd
from numbers import Integral
from itertools import product
from sqlalchemy import String, Float, Integer, Column
from exa.cms.base import BaseMeta, Base, session_factory


class Meta(BaseMeta):
    """Provides lookup methods for :class:`~exa.cms.isotope.Isotope`."""
    def get_by_strid(cls, strid):
        """Get an isotope using a string id."""
        return session_factory().query(cls).filter(cls.strid == strid).one()

    def get_by_symbol(cls, symbol):
        """Get all isotopes with a given element symbol."""
        return session_factory().query(cls).filter(cls.symbol == symbol).all()

    def compute_element(cls, name_or_symbol):
        """
        Get (i.e. compute) the element with the given name or symbol (an
        element"s data is given as an average over isotopic composition).
        """
        iso = cls.to_frame()
        h = ["H", "D", "T"]
        hn = ["hydrogen", "deuterium", "tritium"]
        if len(name_or_symbol) <= 3:
            if name_or_symbol in ["H", "D", "T"]:
                iso = iso[iso["symbol"].isin(h)]
            else:
                iso = iso[iso["symbol"] == name_or_symbol]
        else:
            name_or_symbol = name_or_symbol.lower()
            if name_or_symbol in hn:
                iso = iso[iso["name"].isin(hn)]
            else:
                iso = iso[iso["name"] == name_or_symbol]
        return Element.from_isotopes(iso)

    def _getitem(cls, key):
        """Custom getter that support strid (e.g. "1H") and symbols."""
        if isinstance(key, str):
            if key[0].isdigit():
                return cls.get_by_strid(key)
            elif len(key) <= 3:
                return cls.get_by_symbol(key)
            return cls.get_by_name(key)
        elif isinstance(key, Integral):
            return cls.get_by_pkid(key)
        raise KeyError("Isotope not found for key {}".format(str(key)))


class Isotope(six.with_metaclass(Meta, Base)):
    """
    A variant of a chemical element with a specific proton and neutron count.

        >>> h = Isotope["1H"]
        >>> h.A
        1
        >>> h.Z
        1
        >>> h.mass
        1.0078250321
        >>> Isotope["C"]
        [8C, 9C, 10C, 11C, 12C, 13C, 14C, 15C, 16C, 17C, 18C, 19C, 20C, 21C, 22C]
        >>> Isotope["13C"].szuid
        175
        >>> c = Isotope[57]
        >>> c.A
        13
        >>> c.Z
        6
        >>> c.strid
        "13C"
    """
    A = Column(Integer, nullable=False)
    Z = Column(Integer, nullable=False)
    af = Column(Float)
    eaf = Column(Float)
    color = Column(Integer)
    radius = Column(Float)
    gfactor = Column(Float)
    mass = Column(Float)
    emass = Column(Float)
    name = Column(String(length=16))
    eneg = Column(Float)
    quadmom = Column(Float)
    spin = Column(Float)
    symbol = Column(String(length=3))
    szuid = Column(Integer)
    strid = Column(Integer)

    @classmethod
    def element(cls, name_or_symbol):
        """Compute an element from its component isotopes."""
        return cls.compute_element(name_or_symbol)

    def __repr__(self):
        return "Isotope({0}{1})".format(self.A, self.symbol)


class Element(object):
    """
    An element is computed by taking the representative abundance fractions of
    each isotope having the same number of protons.
    """
    @classmethod
    def from_isotopes(cls, isotopes):
        """
        Static helper function for computing element data from a slice of the
        full isotope table.

        Args:
            isotopes (DataFrame): Slice containing all isotopes of desired element

        Returns:
            element (:class:`~exa.cms.isotope.Element`):
        """
        mass = (isotopes["af"]*isotopes["mass"]).sum()
        emass = mass*(isotopes["af"]*isotopes["emass"]/isotopes["mass"]).sum()
        idx = isotopes["af"].idxmax()
        items = ["A", "Z", "name", "symbol", "radius"]
        anum, znum, name, symbol, radius = isotopes.ix[idx, items]
        return cls(name=name, symbol=symbol, A=anum, Z=znum, mass=mass,
                   emass=emass, radius=radius)

    def __init__(self, name, mass, emass, radius, A, Z, symbol):
        self.name = name
        self.symbol = symbol
        self.A = A
        self.Z = Z
        self.mass = mass
        self.emass = emass

    def __repr__(self):
        return "Element({0})".format(self.symbol)


def elements():
    """
    Create a :class:`~pandas.Series` of :class:`~exa.cms.isotope.Element`
    objects.
    """
    isotopes = Isotope.to_frame()
    isotopes = isotopes[isotopes['af'].notnull()].groupby('name')
    return isotopes.apply(Element.from_isotopes)


def symbol_to_znum():
    """
    Create a "mapper" (:class:`~pandas.Series`) from element symbol to proton
    number ("Z"). This object can be used to quickly transform element symbols
    to proton number via:

    .. code-block:: Python

        mapper = symbol_to_z()
        z_series = symbol_series.map(mapper)
    """
    df = Isotope.to_frame().drop_duplicates("symbol").sort_values("symbol")
    return df.set_index("symbol")["Z"]


def znum_to_symbol():
    """
    Create a mapper from proton number to element symbol.

    See Also:
        Opposite mapper of :func:`~exa.cms.isotope.symbol_to_z`.
    """
    df = Isotope.to_frame().drop_duplicates("Z").sort_values("Z")
    return df.set_index("Z")["symbol"]


def symbol_to_radius():
    """Mapper from symbol pairs to sum of covalent radii."""
    df = Isotope.to_frame().drop_duplicates("symbol")
    symbol = df["symbol"].values
    radius = df["radius"].values
    symbols = [symbol0 + symbol1 for symbol0, symbol1 in product(symbol, symbol)]
    s = pd.Series([radius0 + radius1 for radius0, radius1 in product(radius, radius)])
    s.index = symbols
    return s


def symbol_to_element_mass():
    """Mapper from symbol to element mass."""
    df = Isotope.to_frame()
    df["fmass"] = df["mass"].mul(df["af"])
    s = df.groupby("name").sum()
    mapper = df.drop_duplicates("name").set_index("name")["symbol"]
    s.index = s.index.map(lambda x: mapper[x])
    s = s["fmass"]
    return s


def symbol_to_radius():
    """Mapper from isotope symbol to covalent radius."""
    df = Isotope.to_frame().drop_duplicates("symbol")
    return df.set_index("symbol")["radius"]


def symbol_to_color():
    """Mapper from isotope symbol to color."""
    df = Isotope.to_frame().drop_duplicates("symbol")
    return df.set_index("symbol")["color"]
