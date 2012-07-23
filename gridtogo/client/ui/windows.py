from gridtogo.shared.networkobjects import *
from gi.repository import Gtk
import os

def showModalDialog(parent, messageType, message):
	dialog = Gtk.MessageDialog(parent,
		Gtk.DialogFlags.MODAL,
		messageType,
		Gtk.ButtonsType.OK,
		message)
	dialog.run()
	dialog.destroy()

class SpinnerPopup(Gtk.Window):
	def __init__(self, message):
		pass

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

	def LANModeClicked(self, *args):
		print("LAN Mode")

	def createUserClicked(self, *args):
		self.clientObject.createUserWindowHandler = self.factory.buildWindow("createUserWindow", CreateUserWindowHandler)
		self.clientObject.createUserWindowHandler.window.show_all()

	def loginClicked(self, *args):


		# register our stuff to be called then attempt connection
		self.clientObject.callOnConnected.append(self.onConnectionEstablished)
		#TODO: Read host:port from "Coordination Server" box
		self.clientObject.attemptConnection('localhost', 8017, 5)

	def onConnectionEstablished(self, protocol):
		firname = self.firstNameEntry.get_text()
		lasname = self.lastNameEntry.get_text()
		passwd = self.passwordEntry.get_text()
		grid = self.gridEntry.get_text()
		request = LoginRequest(firname, lasname, passwd, grid)
		self.clientObject.protocol.writeRequest(request)

		# de-register this method
		self.clientObject.callOnConnected.remove(self.onConnectionEstablished)

	def forgotPasswordClicked(self, *args):
		print("forgot password")

	def quitClicked(self, *args):
		self.clientObject.stop()

class CreateUserWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(CreateUserWindowHandler, self).__init__(builder, clientObject, factory, window)
		self.emailEntry = builder.get_object("entryEMail")
		self.firstNameEntry = builder.get_object("entryFirstName")
		self.lastNameEntry = builder.get_object("entryLastName")
		self.passwordEntry = builder.get_object("entryPassword")
		self.passwordRetypeEntry = builder.get_object("entryRetypePassword")

	def destroy(self):
		self.window.destroy()

	def createUserClicked(self, *args):
		email = self.emailEntry.get_text()
		firstName = self.firstNameEntry.get_text()
		lastName = self.firstNameEntry.get_text()
		passwordEntry = self.passwordEntry.get_text()
		passwordRetypeEntry = self.passwordRetypeEntry.get_text()

		if passwordEntry != passwordRetypeEntry:
			showModalDialog(self.window, Gtk.MessageType.ERROR, "Passwords do not match.")
			return

		# Register our method and attempt connection
		self.clientObject.callOnConnected.append(self.connectionEstablished)
		#TODO: Read host:port from "Coordination Server" box
		self.clientObject.attemptConnection('localhost', 8017, 5)
		
	def onCreateUserSuccess(self):
		showModalDialog(self.window, Gtk.MessageType.INFO, CreateUserSuccess().message)
		self.destroy()

	def connectionEstablished(self, protocol):
		email = self.emailEntry.get_text()
		firstName = self.firstNameEntry.get_text()
		lastName = self.lastNameEntry.get_text()
		passwordEntry = self.passwordEntry.get_text()

		request = CreateUserRequest(firstName, lastName, passwordEntry, email)
		self.clientObject.protocol.writeRequest(request)

		# de-register this method
		self.clientObject.callOnConnected.remove(self.connectionEstablished)

	def cancelClicked(self, *args):
		self.destroy()

class MainWindowHandler(WindowHandler):

	def __init__(self, builder, clientObject, factory, window):
		super(MainWindowHandler, self).__init__(builder, clientObject, factory, window)
		
		self.box = Gtk.Box(spacing=6)
		



	def PopulateTable(self):

	def destroy(self):
		self.window.destroy()
