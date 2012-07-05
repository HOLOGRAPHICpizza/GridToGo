using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Linq;
using Gtk;

namespace GridToGo
{
	static class Program
	{
		[STAThread]
		static void Main()
		{
			Application.Init();
			Window myWin = new Window("My first GTK# Application! ");
			myWin.Resize(200, 200);
			myWin.Destroyed += new EventHandler(myWin_Destroyed);
			Label myLabel = new Label();
			myLabel.Text = "Hello World!!!!";
			myWin.Add(myLabel);
			myWin.ShowAll();
			Application.Run();
		}

		static void myWin_Destroyed(object sender, EventArgs e)
		{
			Application.Quit();
		}
	}
}
