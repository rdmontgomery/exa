# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016, Exa Analytics Development Team
# Distributed under the terms of the Apache License 2.0
"""
Tests for :mod:`~exa.cms.editor`
#############################################
Test the functionality of the :class:`~exa.cms.editor.Editor` class and
related functions.
"""
import shutil
import os, gzip, bz2
from io import StringIO, open
from uuid import uuid4
from exa._config import config
from exa.tester import UnitTester
from exa.cms.editors.editor import Editor, concat
if not hasattr(bz2, "open"):
    bz2.open = bz2.BZ2File


editor_string = u"""This string is used as the test for the editor class.

That was a blank line
It contains templates: {template}
and constants: {{constant}}

That was a blank line"""


class TestEditor(UnitTester):
    """
    The tester reads in a contrived example in the root "tests" directory and
    proceeds to test the various functions provided by
    :class:`~exa.cms.editor.Editor`.
    """
    def setUp(self):
        """
        A :class:`~exa.cms.editor.Editor` can be create in three ways,
        from a file, from a stream, and from a string.
        """
        self.path = os.path.join(config['paths']['tmp'], uuid4().hex)
        with open(self.path, 'wb') as f:
            f.write(str.encode(editor_string))
        with open(self.path, "rb") as f_in:
            with gzip.open(self.path + ".gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        with open(self.path, "rb") as f_in:
            with bz2.open(self.path + ".bz2", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        with open(self.path + '.iso-8859-1', 'wb') as f:
            f.write(str.encode(editor_string, encoding='iso-8859-1'))
        self.from_file = Editor(self.path)
        self.from_file_enc = Editor(self.path, encoding='iso-8859-1')
        self.from_gzip = Editor(self.path + ".gz")
        self.from_bz2 = Editor(self.path + ".bz2")
        self.from_stream = Editor(StringIO(editor_string))
        self.from_string = Editor(editor_string)

    def tearDown(self):
        """
        Remove the temporary files generated by the test.
        """
        os.remove(self.path)
        os.remove(self.path + ".gz")
        os.remove(self.path + ".bz2")
        os.remove(self.path + ".iso-8859-1")

    def test_editor_input_methods(self):
        """
        Test to make sure all the support input (**read_\***) were read in
        correctly. This function actually tests
        :func:`~exa.cms.editor.Editor.__eq__`.
        """
        self.assertEqual(self.from_file, self.from_file_enc)
        self.assertEqual(self.from_file, self.from_gzip)
        self.assertEqual(self.from_file, self.from_bz2)
        self.assertEqual(self.from_file, self.from_stream)
        self.assertEqual(self.from_file, self.from_string)

    def test_tmpl_cnst(self):
        """
        Test :func:`~exa.cms.editor.Editor.templates` and
        :func:`~exa.cms.editor.Editor.constants`.
        """
        self.assertEqual(self.from_file.templates, ['template'])
        self.assertEqual(self.from_file.constants, ['constant'])

    def test_head_tail(self):
        """
        Test :func:`~exa.cms.editors.editor.Editor.head` and
        :func:`~exa.cms.editor.Editor.tail`.
        """
        self.assertEqual(self.from_file.head(1), self.from_file._lines[0])
        self.assertEqual(self.from_file.tail(1), self.from_file._lines[-1])

    def test_insert(self):
        """
        Test :func:`~exa.cms.editors.editor.Editor.append`,
        Test :func:`~exa.cms.editors.editor.Editor.prepend`, and
        :func:`~exa.cms.editors.editor.Editor.insert`.
        """
        test = "new\nlines"
        self.from_file.append(test)
        self.assertEqual(str(self.from_file[-1]), "lines")
        self.from_file.prepend(test)
        self.assertEqual(str(self.from_file[1]), "lines")
        del self.from_file[0]
        del self.from_file[0]
        del self.from_file[-1]
        del self.from_file[-1]
        self.from_file.insert(-1, test)
        self.assertEqual(str(self.from_file[-2]), "lines")
        del self.from_file[-2]
        del self.from_file[-2]

    def test_replace(self):
        """
        Test :func:`~exa.cms.editors.editor.Editor.replace`.
        """
        rp0 = "This string is used as the test for the editor class."
        rp1 = "replacement"
        self.from_file.replace(rp0, rp1)
        self.assertEqual(str(self.from_file[0]), rp1)
        self.from_file.replace(rp1, rp0)

    def test_find_next(self):
        """
        Test :func:`~exa.cms.editors.editor.Editor.find_next`.
        """
        rp = "That was a blank line"
        self.assertEqual(self.from_file.find_next(rp, "keys", True), 6)  # Cursor 0 -> 6
        self.assertEqual(self.from_file.find_next(rp, "keys"), 2)        # 6 -> 2
        self.assertEqual(self.from_file.find_next(rp, "keys"), 6)        # 2 -> 6

    def test_concat(self):
        """
        Test :func:`~exa.cms.editors.editor.concat`.
        """
        ed = concat(self.from_file, self.from_file)
        self.assertEqual(len(ed), 2*len(self.from_file))

    def test_remove_blank_lines(self):
        """
        Test :func:`~exa.cms.editors.editor.Editor.remove_blank_lines`.
        """
        self.from_gzip.remove_blank_lines()
        self.assertEqual(len(self.from_gzip), len(self.from_file) - 2)
