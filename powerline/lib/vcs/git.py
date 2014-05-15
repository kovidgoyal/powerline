# vim:fileencoding=utf-8:noet

import os
import re

from powerline.lib.vcs import get_branch_name as _get_branch_name, get_file_status

_ref_pat = re.compile(br'ref:\s*refs/heads/(.+)')

def branch_name_from_config_file(directory, config_file):
	try:
		with open(config_file, 'rb') as f:
			raw = f.read()
	except EnvironmentError:
		return os.path.basename(directory)
	m = _ref_pat.match(raw)
	if m is not None:
		return m.group(1).decode('utf-8', 'replace')
	return raw[:7]

def git_directory(directory):
	path = os.path.join(directory, '.git')
	if os.path.isfile(path):
		with open(path, 'rb') as f:
			raw = f.read().partition(b':')[2].strip()
			return os.path.abspath(os.path.join(directory, raw))
	else:
		return path

def get_branch_name(base_dir):
	head = os.path.join(git_directory(base_dir), 'HEAD')
	return _get_branch_name(base_dir, head, branch_name_from_config_file)

def do_status(directory, path, func):
	if path:
		gitd = git_directory(directory)
		# We need HEAD as without it using fugitive to commit causes the
		# current file's status (and only the current file) to not be updated
		# for some reason I cannot be bothered to figure out.
		return get_file_status(
			directory, os.path.join(gitd, 'index'),
			path, '.gitignore', func, extra_ignore_files=tuple(os.path.join(gitd, x) for x in ('logs/HEAD', 'info/exclude')))
	return func(directory, path)

from subprocess import Popen, PIPE

def readlines(cmd, cwd):
	p = Popen(cmd, shell=False, stdout=PIPE, stderr=PIPE, cwd=cwd)
	p.stderr.close()
	with p.stdout:
		for line in p.stdout:
			yield line[:-1].decode('utf-8')

def gitcmd(directory, *args):
	return readlines(('git',) + args, directory)

class Repository(object):
	__slots__ = ('directory', 'ignore_event')

	def __init__(self, directory):
		self.directory = os.path.abspath(directory)

	def ignore_event(self, path, name):
		return path.endswith('.git') and name == 'index.lock'

	def do_status(self, directory, path):
		if path:
			try:
				return next(gitcmd(directory, 'status', '--porcelain', '--ignored', '--', path))[:2]
			except StopIteration:
				return None
		else:
			wt_column = ' '
			index_column = ' '
			untracked_column = ' '
			for line in gitcmd(directory, 'status', '--porcelain'):
				if line[0] == '?':
					untracked_column = 'U'
					continue
				elif line[0] == '!':
					continue

				if line[0] != ' ':
					index_column = 'I'

				if line[1] != ' ':
					wt_column = 'D'

			r = wt_column + index_column + untracked_column
			return r if r != '   ' else None

	def status(self, path=None):
		return do_status(self.directory, path, self.do_status)

	def branch(self):
		return get_branch_name(self.directory)
