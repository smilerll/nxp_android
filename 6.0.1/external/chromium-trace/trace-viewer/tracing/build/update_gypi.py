# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import os
import re
import sys

tracing_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '..', '..'))
if tracing_path not in sys.path:
  sys.path.append(tracing_path)

from tracing.build import check_common
from tracing import tracing_project


class _Token(object):

  def __init__(self, data, id=None):
    self.data = data
    if id:
      self.id = id
    else:
      self.id = 'plain'


class BuildFile(object):

  def __init__(self, text, file_groups):
    self._file_groups = file_groups
    self._tokens = [token for token in self._Tokenize(text)]

  def _Tokenize(self, text):
    rest = text
    token_regex = self._TokenRegex()
    while len(rest):
      m = token_regex.search(rest)
      if not m:
        # In `rest', we couldn't find a match.
        # So, lump the entire `rest' into a token
        # and stop producing any more tokens.
        yield _Token(rest)
        return
      min_index, end_index, matched_token = self._ProcessMatch(m)

      if min_index > 0:
        yield _Token(rest[:min_index])

      yield matched_token
      rest = rest[end_index:]

  def Update(self, files_by_group):
    for token in self._tokens:
      if token.id in files_by_group:
        token.data = self._GetReplacementListAsString(
            token.data,
            files_by_group[token.id])

  def Write(self, f):
    for token in self._tokens:
      f.write(token.data)

  def _ProcessMatch(self, match):
    raise Exception("Not implemented.")

  def _TokenRegex(self):
    raise Exception("Not implemented.")

  def _GetReplacementListAsString(self, existing_list_as_string, filelist):
    raise Exception("Not implemented.")


class GypiFile(BuildFile):

  def _ProcessMatch(self, match):
    min_index = match.start(2)
    end_index = match.end(2)
    token = _Token(match.string[min_index:end_index],
                   id=match.groups()[0])
    return min_index, end_index, token

  def _TokenRegex(self):
    # regexp to match the following:
    #   'file_group_name': [
    #     'path/to/one/file.extension',
    #     'another/file.ex',
    #   ]
    # In the match,
    # group 1 is : 'file_group_name'
    # group 2 is : """  'path/to/one/file.extension',\n  'another/file.ex',\n"""
    regexp_str = "'(%s)': \[\n(.+?) +\],?\n" % "|".join(self._file_groups)
    return re.compile(regexp_str, re.MULTILINE | re.DOTALL)

  def _GetReplacementListAsString(self, existing_list_as_string, filelist):
    list_entry = existing_list_as_string.splitlines()[0]
    prefix, entry, suffix = list_entry.split("'")
    return "".join(["'".join([prefix, filename, suffix + '\n'])
                    for filename in filelist])


def _GroupFiles(fileNameToGroupNameFunc, filenames):
  file_groups = collections.defaultdict(lambda: [])
  for filename in filenames:
    file_groups[fileNameToGroupNameFunc(filename)].append(filename)
  for group in file_groups:
    file_groups[group].sort()
  return file_groups


def _UpdateBuildFile(filename, build_file_class):
  with open(filename, 'r') as f:
    build_file = build_file_class(f.read(), check_common.FILE_GROUPS)
  files_by_group = _GroupFiles(check_common.GetFileGroupFromFileName,
                               check_common.GetKnownFiles())
  build_file.Update(files_by_group)
  with open(filename, 'w') as f:
    build_file.Write(f)


def UpdateGypi():
  tvp = tracing_project.TracingProject()
  _UpdateBuildFile(
      os.path.join(tvp.tracing_root_path, 'trace_viewer.gypi'), GypiFile)


def Update():
  UpdateGypi()
