from gi.repository import Gtk
import os

class WindowFactory(object):
	def __init__(self, clientObject):
		self.clientObject = clientObject

	def buildWindow(self, windowName, handlerClass):
		builder = Gtk.Builder()
		global PROJECT_ROOT_DIRECTORY
		builder.add_from_file(os.path.join(self.clientObject.projectRoot, "gridtogo", 'client', 'ui', windowName + '.glade'))
		builder.connect_signals(handlerClass(self.clientObject))
		return builder.get_object(windowName)

class WindowHandler(object):
	def __init__(self, clientObject):
		self.clientObject = clientObject

class LoginWindowHandler(WindowHandler):
	def LANModeClicked(self, *args):
		print("LAN Mode")

	def createUserClicked(self, *args):
		print("Create User")

	def loginClicked(self, *args):
		print("login")

	def forgotPasswordClicked(self, *args):
		print("forgot password")

	def quitClicked(self, *args):
		self.clientObject.stop()
