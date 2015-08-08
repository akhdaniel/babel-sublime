import json
import os
import platform
import sublime
import sublime_plugin
import subprocess

# monkeypatch `Region` to be iterable
sublime.Region.totuple = lambda self: (self.a, self.b)
sublime.Region.__iter__ = lambda self: self.totuple().__iter__()

BIN_PATH = os.path.join(
	sublime.packages_path(),
	os.path.dirname(os.path.realpath(__file__)),
	'babel-transform.js'
)

class BabelCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		selected_text = self.get_text()
		code = self.babelify(selected_text)

		if code:
			w = sublime.Window.new_file(self.view.window())
			w.settings().set('default_extension', 'js')
			w.set_syntax_file(self.view.settings().get('syntax'))
			w.set_scratch(True)
			w.insert(edit, 0, code)

	def babelify(self, data):
		try:
			return node_bridge(data, BIN_PATH, [json.dumps({
				'filename': self.view.file_name(),
				'debug': self.get_setting('debug'),
				'ensure_newline_at_eof': self.get_setting('ensure_newline_at_eof'),
				'use_local_babel': self.get_setting('use_local_babel'),
				'node_modules': self.get_setting('node_modules'),
				'options': self.get_setting('options')
			})])
		except Exception as e:
			return str(e)

	def get_text(self):
		if not self.has_selection():
			region = sublime.Region(0, self.view.size())
			return self.view.substr(region)

		selected_text = ''
		for region in self.view.sel():
			selected_text = selected_text + self.view.substr(region) + '\n'
		return selected_text

	def has_selection(self):
		for sel in self.view.sel():
			start, end = sel
			if start != end:
				return True
		return False

	def get_setting(self, key):
		settings = self.view.settings().get('Babel')
		if settings is None:
			settings = sublime.load_settings('Babel.sublime-settings')
		return settings.get(key)


def node_bridge(data, bin, args=[]):
	env = None
	startupinfo = None
	if platform.system() == 'Darwin':
		# GUI apps in OS X doesn't contain .bashrc/.zshrc set paths
		env = os.environ.copy()
		env['PATH'] += ':/usr/local/bin'
	if platform.system() == 'Windows':
		startupinfo = subprocess.STARTUPINFO()
		startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
	try:
		p = subprocess.Popen(
			['node', bin] + args,
			stdout=subprocess.PIPE,
			stdin=subprocess.PIPE,
			stderr=subprocess.PIPE,
			env=env,
			startupinfo=startupinfo
		)
	except OSError:
		raise Exception('Error: Couldn\'t find "node" in "%s"' % env['PATH'])
	stdout, stderr = p.communicate(input=data.encode('utf-8'))
	stdout = stdout.decode('utf-8')
	stderr = stderr.decode('utf-8')
	if stderr:
		raise Exception('Error: %s' % stderr)
	else:
		return stdout
