"""
Backend to the console plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
"""
# this file is a modified version of source code from the Accerciser project
# http://live.gnome.org/accerciser

# this file was modified yet again to fix the 'Home' bug - Brian Parma
# this file was modified again for the yai project

import gtk
import re
import sys
import os
import pango
from StringIO import StringIO

#Strange error on Windows
if not sys.argv:
  sys.argv = [""]

try:
  import IPython
except Exception,e:
  raise ImportError, "Error importing IPython (%s)" % str(e)

#ansi_colors =  {'0;30': 'Black',
#                '0;31': 'Red',
#                '0;32': 'Green',
#                '0;33': 'Brown',
#                '0;34': 'Blue',
#                '0;35': 'Purple',
#                '0;36': 'Cyan',
#                '0;37': 'LightGray',
#                '1;30': 'DarkGray',
#                '1;31': 'DarkRed',
#                '1;32': 'SeaGreen',
#                '1;33': 'Yellow',
#                '1;34': 'LightBlue',
#                '1;35': 'MediumPurple',
#                '1;36': 'LightCyan',
#                '1;37': 'White'}

# Tango Colors (from gnome-terminal)
ansi_colors =  {'0;30': '#2e2e34343636',
                '0;31': '#cccc00000000',
                '0;32': '#4e4e9a9a0606',
                '0;33': '#c4c4a0a00000',
                '0;34': '#34346565a4a4',
                '0;35': '#757550507b7b',
                '0;36': '#060698989a9a',
                '0;37': '#d3d3d7d7cfcf',
                '1;30': '#555557575353',
                '1;31': '#efef29292929',
                '1;32': '#8a8ae2e23434',
                '1;33': '#fcfce9e94f4f',
                '1;34': '#72729f9fcfcf',
                '1;35': '#adad7f7fa8a8',
                '1;36': '#3434e2e2e2e2',
                '1;37': '#eeeeeeeeecec'}

class IterableIPShell:
  def __init__(self,argv=None,user_ns=None,user_global_ns=None,
               cin=None, cout=None,cerr=None, input_func=None):
    if input_func:
      self.input_func = input_func
    if cin:
      self.cin = cin
    if cout:
      self.cout = cout
    if cerr:
      self.cerr = cerr

    if argv is None:
      argv=[]

    # This is to get rid of the blockage that occurs during
    # IPython.Shell.InteractiveShell.user_setup()
    IPython.iplib.raw_input = lambda x: None

    os.environ['TERM'] = 'dumb'
    excepthook = sys.excepthook
    if user_global_ns:
      user_global_ns.update({"shell":self})
    self.IP = IPython.Shell.make_IPython(argv,user_ns=user_ns,
                                         user_global_ns=user_global_ns,
                                         embedded=True,
                                         shell_class=IPython.Shell.InteractiveShell)
    self.IP.system = lambda cmd: self.shell(self.IP.var_expand(cmd),
                                            header='IPython system call: ',
                                            verbose=self.IP.rc.system_verbose)
    sys.excepthook = excepthook
    self.iter_more = 0
    self.history_level = 0
    self.complete_sep =  re.compile('[\s\{\}\[\]\(\)]')

  def execute(self):
    self.history_level = 0
    if self.cout:
      origcout = IPython.Shell.Term.cout
      IPython.Shell.Term.cout = self.cout
      orig_stdout = sys.stdout
      sys.stdout = self.cout
    if self.cerr:
      orig_cerr = IPython.Shell.Term.cerr
      IPython.Shell.Term.cerr = self.cerr
    line = None
    if self.input_func:
      original_raw_input = IPython.iplib.raw_input_original
      IPython.iplib.raw_input_original = self.input_func
      
    sys_displayhook = sys.displayhook
    sys.displayhook = self.IP.outputcache
    try:
      line = self.IP.raw_input(None, self.iter_more)
      if self.IP.autoindent:
        self.IP.readline_startup_hook(None)
    except KeyboardInterrupt:
      self.IP.write('\nKeyboardInterrupt\n')
      self.IP.resetbuffer()
      # keep cache in sync with the prompt counter:
      self.IP.outputcache.prompt_count -= 1

      if self.IP.autoindent:
        self.IP.indent_current_nsp = 0
      self.iter_more = 0
    except:
      self.IP.showtraceback()
    else:
      for l in line.split("\n"):
        self.iter_more = self.IP.push(l)
      if (self.IP.SyntaxTB.last_syntax_error and
          self.IP.rc.autoedit_syntax):
        self.IP.edit_syntax_error()
    if self.iter_more:
      self.prompt = str(self.IP.outputcache.prompt2).strip()
      if self.IP.autoindent:
        self.IP.readline_startup_hook(self.IP.pre_readline)
    else:
      self.prompt = str(self.IP.outputcache.prompt1).strip()

    if self.cerr:
      IPython.Shell.Term.cerr = orig_cerr
    if self.cout:
      IPython.Shell.Term.cout = origcout
    if self.input_func:
      IPython.iplib.raw_input_original = original_raw_input
    sys.stdout = orig_stdout
    sys.displayhook = sys_displayhook

  def historyBack(self):
    self.history_level -= 1
    return self._getHistory()

  def historyForward(self):
    if self.history_level != 0:
      self.history_level += 1
    return self._getHistory()

  def _getHistory(self):
    try:
      rv = self.IP.user_ns['In'][self.history_level].strip('\n')
    except IndexError:
      self.history_level = 0
      rv = ''
    return rv

  def updateNamespace(self, ns_dict):
    self.IP.user_ns.update(ns_dict)

  def complete(self, line):
    split_line = self.complete_sep.split(line)
    possibilities = self.IP.complete(split_line[-1])
    if possibilities:
      common_prefix = reduce(self._commonPrefix, possibilities)
      completed = line[:-len(split_line[-1])]+common_prefix
    else:
      completed = line
    return completed, possibilities

  def _commonPrefix(self, str1, str2):
    for i in range(len(str1)):
      if not str2.startswith(str1[:i+1]):
        return str1[:i]
    return str1

  def shell(self, cmd,verbose=0,debug=0,header=''):
    print 'Shell'
    stat = 0
    if verbose or debug: print header+cmd
    # flush stdout so we don't mangle python's buffering
    if not debug:
      input, output = os.popen4(cmd)
      print output.read()
      output.close()
      input.close()

class ConsoleView(gtk.TextView):
  def __init__(self):
    gtk.TextView.__init__(self)
    self.modify_font(pango.FontDescription('Mono'))
    self.set_cursor_visible(True)
    self.text_buffer = self.get_buffer()
    self.mark = self.text_buffer.create_mark('scroll_mark',
                                             self.text_buffer.get_end_iter(),
                                             False)
    for code in ansi_colors:
      self.text_buffer.create_tag(code,
                                  foreground=ansi_colors[code],
                                  weight=700)
    self.text_buffer.create_tag('0')
    self.text_buffer.create_tag('notouch', editable=False)
    self.color_pat = re.compile('\x01?\x1b\[(.*?)m\x02?')
    self.line_start = \
                self.text_buffer.create_mark('line_start',
                        self.text_buffer.get_end_iter(), True
                )
    self.connect('key-press-event', self._onKeypress)
    self.last_cursor_pos = 0

  def write(self, text, editable=False, iter = None):
    segments = self.color_pat.split(text)
    segment = segments.pop(0)
    start_mark = self.text_buffer.create_mark(None,
                                              self.text_buffer.get_end_iter(),
                                              True)
    if iter is None:
      iter = self.text_buffer.get_end_iter()
    self.text_buffer.insert(iter, segment)

    if segments:
      #Even numbered tags should be ansi_tag. Odd numbered tags should be text (this seems to be the only way to avoid collision problems for the moment).
      for i,segment in enumerate(segments):
        if i%2==0:
          tag = segment
          self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(),
                                             segments[i+1], tag)
    if not editable:
      self.text_buffer.apply_tag_by_name('notouch',
                                         self.text_buffer.get_iter_at_mark(start_mark),
                                         self.text_buffer.get_end_iter())
    self.text_buffer.delete_mark(start_mark)
    self.text_buffer.move_mark(self.mark, self.text_buffer.get_end_iter())
    self.scroll_mark_onscreen(self.mark)

  #For testing only
  def rawwrite(self, text, editable=False, iter = None):
    if iter is None:
      iter = self.text_buffer.get_end_iter()
    self.text_buffer.insert(iter, text)
    self.scroll_mark_onscreen(self.mark)

  def showPrompt(self, prompt):
    self.write(prompt)
    self.text_buffer.move_mark(self.line_start,self.text_buffer.get_end_iter())

  def changeLine(self, text):
    iter = self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.delete(self.text_buffer.get_iter_at_mark(self.line_start), iter)
    self.write(text, True)

  def changeLineToMark(self, text):
    start = self.text_buffer.get_iter_at_mark(self.line_start)
    end = self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert())
    self.text_buffer.delete(start, end)
    self.write(text, True, iter=start)

  def getCurrentLine(self):
    rv = self.text_buffer.get_slice(self.text_buffer.get_iter_at_mark(self.line_start),
				    self.text_buffer.get_end_iter(), False)
    return rv

  def getCurrentLineToMark(self):
    rv = self.text_buffer.get_slice(self.text_buffer.get_iter_at_mark(self.line_start),
				    self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert()))
    return rv

  def showReturned(self, text):
    iter = self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.apply_tag_by_name('notouch',
                                       self.text_buffer.get_iter_at_mark(self.line_start),
                                       iter)
    self.write('\n'+text)
    if text:
      self.write('\n')
    self.showPrompt(self.prompt)
    self.text_buffer.move_mark(self.line_start,self.text_buffer.get_end_iter())
    self.text_buffer.place_cursor(self.text_buffer.get_end_iter())

  def _onKeypress(self, obj, event):
    keys = [gtk.keysyms.Delete,gtk.keysyms.Home,gtk.keysyms.BackSpace,
            gtk.keysyms.End]   # catch these keys
    if (not event.string) and (not event.keyval in keys):
      return
    insert_mark = self.text_buffer.get_insert()
    insert_iter = self.text_buffer.get_iter_at_mark(insert_mark)
    selection_mark = self.text_buffer.get_selection_bound()
    selection_iter = self.text_buffer.get_iter_at_mark(selection_mark)
    start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
    if event.keyval == gtk.keysyms.Home :
        self.text_buffer.place_cursor(start_iter)
        return True # stop other handlers
    if start_iter.compare(insert_iter) <= 0 and \
          start_iter.compare(selection_iter) <= 0:
        return
    if event.keyval == gtk.keysyms.BackSpace:
        self.text_buffer.place_cursor(self.text_buffer.get_end_iter())
        return
    elif start_iter.compare(insert_iter) > 0 and \
          start_iter.compare(selection_iter) > 0:
        self.text_buffer.place_cursor(start_iter)
    elif insert_iter.compare(selection_iter) < 0:
        self.text_buffer.move_mark(insert_mark, start_iter)
    elif insert_iter.compare(selection_iter) > 0:
        self.text_buffer.move_mark(selection_mark, start_iter)



def keyPress(widget, event):
  return widget.keyPress(widget, event)

class IPythonView(ConsoleView, IterableIPShell):
  def __init__(self, user_global_ns=None):
    ConsoleView.__init__(self)
    self.cout = StringIO()
    self.interrupt = False
    IterableIPShell.__init__(self, cout=self.cout,cerr=self.cout,
                             input_func=self.raw_input, user_global_ns=user_global_ns,
                             argv=['-colors','LightBG'])
    self.connect('key_press_event', self.keyPress)
    self.execute()
    self.cout.truncate(0)
    self.showPrompt(self.prompt)

  def raw_input(self, prompt=''):
    if self.interrupt:
      self.interrupt = False
      raise KeyboardInterrupt
    return self.getCurrentLine()

  def keyPress(self, widget, event):
    if event.state & gtk.gdk.CONTROL_MASK and event.keyval == 99:
      self.interrupt = True
      self._processLine()
      return True
    elif event.keyval in [gtk.keysyms.Return, gtk.keysyms.KP_Enter]:
      self._processLine()
      return True
    elif event.keyval == gtk.keysyms.Up:
      self.changeLine(self.historyBack())
      return True
    elif event.keyval == gtk.keysyms.Down:
      self.changeLine(self.historyForward())
      return True
    elif event.keyval == gtk.keysyms.Tab:
      if not self.getCurrentLine().strip():
        return False
      rest = self.text_buffer.get_slice(self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert()),
      				self.text_buffer.get_end_iter(), False)
      completed, possibilities = self.complete(self.getCurrentLineToMark())
      if len(possibilities) > 1:
        slice = self.getCurrentLine()
        self.write('\n')
        for symbol in possibilities:
          self.write(symbol+'\n')
        self.showPrompt(self.prompt)
      if completed:
	self.changeLine(completed)
	insert_mark = self.text_buffer.get_insert()
 	selection_mark = self.text_buffer.get_selection_bound()
	start_mark = self.text_buffer.create_mark(None,
						  self.text_buffer.get_end_iter(),
						  True)
	self.write(rest, True)
	middle = self.text_buffer.get_iter_at_mark(start_mark)
	self.text_buffer.move_mark(insert_mark, middle)
	self.text_buffer.move_mark(selection_mark, middle)
      else:
        self.changeLine(slice)
      return True

  def _processLine(self):
    self.history_pos = 0
    self.execute()
    rv = self.cout.getvalue()
    if rv: rv = rv.strip('\n')
    self.showReturned(rv)
    self.cout.truncate(0)

def scrolled_ipyconsole(width, height, **kwargs):
  #Generate an IPython console inside a scrolled window
  sw = gtk.ScrolledWindow()
  if "user_global_ns" not in kwargs:
    kwargs["user_global_ns"] = {"scrolledwin":sw}
  ipv = IPythonView(**kwargs) #Also remember the variable name "shell"
  sw.add_with_viewport(ipv)
  sw.set_size_request(-1,height)
  sw.set_size_request(width,height)

  def changedv(widget, event, data=None ):
    """ Callback. Scrolled in console."""
    adj = widget.parent.get_vadjustment()
    adj.set_value(adj.upper - adj.page_size)

  ipv.connect('size-allocate', changedv)
  return sw, ipv

if __name__ == "__main__":
  window = gtk.Window(gtk.WINDOW_TOPLEVEL)
  window.connect("destroy", lambda w: gtk.main_quit())

  sw, ipv = scrolled_ipyconsole(500, 300)

  window.add(sw)
  window.show_all()
  gtk.main()
