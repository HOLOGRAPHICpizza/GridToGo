from gridtogo.shared.networkobjects import *
from gi.repository import Gtk
import os

class WindowFactory(object):
	def __init__(self, clientObject):
		self.clientObject = clientObject

	def buildWindow(self, windowName, handlerClass):
		builder = Gtk.Builder()
		global PROJECT_ROOT_DIRECTORY
		builder.add_from_file(os.path.join(self.clientObject.projectRoot, "gridtogo", 'client', 'ui', windowName + '.glade'))
		handler = handlerClass(builder, self.clientObject, self, builder.get_object(windowName))
		builder.connect_signals(handler)
		return handler

class WindowHandler(object):
	def __init__(self, builder, clientObject, factory, window):
		self.builder = builder
		self.clientObject = clientObject
		self.factory = factory
		self.window = window

class LoginWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(LoginWindowHandler, self).__init__(builder, clientObject, factory, window)
		self.firstNameEntry = builder.get_object("firstName")
		self.lastNameEntry = builder.get_object("lastName")
		self.passwordEntry = builder.get_object("password")
		self.gridEntry = builder.get_object("grid")

		# register our stuff to be called
		self.clientObject.callOnConnected.append(self.onConnectionEstablished)

	def LANModeClicked(self, *args):
		print("LAN Mode")

	def createUserClicked(self, *args):
		w = self.factory.buildWindow("createUserWindow", CreateUserWindowHandler)
		w.window.show_all()

	def loginClicked(self, *args):
		#TODO: Read host:port from "Coordination Server" box
		#TODO: remove the print statements from connection process and use a spinner and msg boxes
		self.clientObject.attemptConnection('localhost', 8017, 5)

	def onConnectionEstablished(self, protocol):
		
		firname = self.firstNameEntry.get_text()
		lasname = self.lastNameEntry.get_text()
		passwd = self.passwordEntry.get_text()
		grid = self.gridEntry.get_text()
		request = LoginRequest(firname, lasname, passwd, grid)
		self.clientObject.protocol.writeRequest(request)

	def forgotPasswordClicked(self, *args):
		print("forgot password")

	def quitClicked(self, *args):
		self.clientObject.stop()

#TODO: Put this code in the right place.
class CreateUserWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(CreateUserWindowHandler, self).__init__(builder, clientObject, factory, window)
		self.emailEntry = builder.get_object("entryEMail")
		self.firstNameEntry = builder.get_object("entryFirstName")
		self.lastNameEntry = builder.get_object("entryLastName")
		self.passwordEntry = builder.get_object("entryPassword")
		self.passwordRetypeEntry = builder.get_object("entryRetypePassword")

	def createUserClicked(self, *args):
		email = self.emailEntry.get_text()
		firstName = self.firstNameEntry.get_text()
		lastName = self.firstNameEntry.get_text()
		passwordEntry = self.passwordEntry.get_text()
		passwordRetypeEntry = self.passwordRetypeEntry.get_text()

		if passwordEntry != passwordRetypeEntry:
			dialog = Gtk.MessageDialog(self.window,
						Gtk.DialogFlags.DESTROY_WITH_PARENT,
						Gtk.MessageType.ERROR,
						Gtk.ButtonsType.OK,
						"Passwords do not match.")
			dialog.run()
			dialog.destroy()
			return

		#TODO: Update this code to be like LoginWindowHandler
#		self.clientObject.factory.onConnectionEstablished = self.connectionEstablished
#		self.clientObject.factory.onUsernameConflict = self.onUsernameConflict
#		self.clientObject.factory.onCreateUserSuccess = self.onCreateUserSuccess
		#reactor.connectTCP("localhost", 8017, self.clientObject.factory)
	
	def onUsernameConflict(self):
		dialog = Gtk.MessageDialog(self.window,
					Gtk.DialogFlags.DESTROY_WITH_PARENT,
					Gtk.MessageType.ERROR,
					Gtk.ButtonsType.OK,
					"Username conflict.")
		dialog.run()
		dialog.destroy()
		
	def onCreateUserSuccess(self):
		dialog = Gtk.MessageDialog(self.window,
					Gtk.DialogFlags.DESTROY_WITH_PARENT,
					Gtk.MessageType.SUCCESS,
					Gtk.ButtonsType.OK,
					"User created successfully!")
		dialog.run()
		dialog.destroy()
		self.window.destroy()

	def connectionEstablished(self):
		email = self.emailEntry.get_text()
		firstName = self.firstNameEntry.get_text()
		lastName = self.lastNameEntry.get_text()
		passwordEntry = self.passwordEntry.get_text()

		request = CreateUserRequest(firstName, lastName, passwordEntry, email)
		self.clientObject.writeRequest(request)

	def cancelClicked(self, *args):
		self.window.destroy()
