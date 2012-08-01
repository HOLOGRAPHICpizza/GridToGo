from gi.repository import Gtk

def showModalDialog(parent, messageType, message):
	"""
	Examples of calls, blocks until user hits OK:
		showModalDialog(self.window, Gtk.MessageType.ERROR, "Passwords do not match.")
		showModalDialog(None, Gtk.MessageType.INFO, "Hello, world!")
	"""
	dialog = Gtk.MessageDialog(parent,
		Gtk.DialogFlags.MODAL,
		messageType,
		Gtk.ButtonsType.OK,
		message)
	dialog.run()
	dialog.destroy()