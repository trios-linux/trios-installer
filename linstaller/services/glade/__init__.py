# -*- coding: utf-8 -*-
# linstaller glade service - (C) 2012 Eugenio "g7" Paolantonio and the Semplice Team.
# All rights reserved. Work released under the GNU GPL license, version 3 or later.
#
# This is a service of linstaller, should not be executed as a standalone application.

import linstaller.core.service
import linstaller.core.main as m

import notify2

import os
import time

import threading

import locale, t9n.library
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain("linstaller", "/usr/share/locale")
#gettext.bindtextdomain("linstaller", "/usr/share/locale")
#gettext.textdomain("linstaller")
#_ = gettext.gettext

_ = t9n.library.translation_init("linstaller")

from linstaller.core.main import info, warn, verbose

from gi.repository import Gtk, GObject, Gdk

GObject.threads_init()

# Get linstaller main dir (a bit hacky and ugly)
MAINDIR = os.path.join(os.path.dirname(m.__file__), "..")
MODULESDIR = os.path.join(MAINDIR, "modules/")

uipath = os.path.join(MAINDIR, "services/glade/base_ui.glade")

### HEADER TYPES ###
head_col_light = {"error":"#F07568","info":"#729fcf","ok":"#73d216","hold":"#f57900"}
#head_col = {"error":"#a40000", "info":"#204a87", "ok":"#4e9a06", "hold":"#ce5c00"}
head_col = {"error":"#a40000","info":"#204a87","ok":"#4e9a06","hold":"#ce5c00"}
head_ico = {"info":"info","error":"error","ok":"gtk-apply","hold":"system-run"}

class Service(linstaller.core.service.Service):
	""" The glade service is the core of the linstaller's glade frontend.
	A GUI is created and maintained by the service, and linstaller will
	trigger modules changes (whose GUIs are preloaded by this service), 
	thus reducing lags and presenting a cleaner environment. """
	
	def __init__(self, main_settings, service_space, cfg):
		""" __init__ override. """
		
		linstaller.core.service.Service.__init__(self, main_settings, service_space, cfg)

		self.on_inst = False
		self.quota = None
		self.old_module = None
	
	def return_color(self, typ):
		""" Returns color for typ. """
		
		if typ in head_col_light:
			return head_col_light[typ]
		else:
			return None
	
	def free_previous_modules(self, limit):
		""" Removes GUI objects of modules ranging from 0 to limit.
		
		limit should be the name of the module which should be leaved as-is."""
		
		for module in self.main_settings["modules"]:
			if module == limit: break
			
			verbose("Freeing up stuff of %s..." % module)
			del self.modules_objects[module]
	
	def on_module_change(self):
		""" Handle modules. """
				
		# Check if the frontend is glade (or a derivative), otherwise it's useless ;-)
		if "glade" in self.main_settings["frontend"]:
			moduletype = self.current_module.package.split(".")[-1]
			
			if not self.on_inst and moduletype == "inst":
				# Point of non-return (do not worry, we can actually return :D). Disable Next/Back/Cancel buttons, hide pages and show the progressbar boxes.
				
				GObject.idle_add(self.cancel_button.set_sensitive, False)
				GObject.idle_add(self.back_button.set_sensitive, False)
				GObject.idle_add(self.next_button.set_sensitive, False)
				#self.pages.hide()
				GObject.idle_add(self.inst.show_all)
				
				## Calculate how many steps are possible by every module (100.0 / len(inst_modules))
				try:
					self.possible = 1.0 / len(self.inst_modules)
				except ZeroDivisionError:
					self.possible = 0.0
				self.current = 0.0
				
				self.free_previous_modules(self.current_module.package.replace("linstaller.modules.",""))
				
				self.on_inst = True
			elif self.on_inst and moduletype == "front":
				# hmm... new module is frontend, need to restore some things...
				
				GObject.idle_add(self.cancel_button.set_sensitive, True)
				GObject.idle_add(self.back_button.set_sensitive, False) # We can't go back!
				GObject.idle_add(self.next_button.set_sensitive, True)
				#self.pages.hide()
				GObject.idle_add(self.inst.hide)

				self.on_inst = False	
			elif self.on_inst:
				# Finish older module's percentage
				if self.old_module in self.inst_modules: self.progress_finish_percentage()
				# Ensure we have the next button insensitive
				GObject.idle_add(self.next_button.set_sensitive, False)
			
			
			self.old_module = self.current_module.package.replace("linstaller.modules.","")
		
	def progress_set_text(self, text):
		""" Sets the text of the progress label """
		
		GObject.idle_add(self.progress_label.set_markup, "<i>%s</i>" % text)
		
	def progress_set_quota(self, quota=100):
		""" Sets the final quota for this job. """
		
		self.quota = float(quota)
	
	def progress_get_quota(self):
		""" Returns the current progress quota. """
		
		return self.quota
	
	def progress_set_percentage(self, final):
		""" Update the progress percentage with final. """
		
		try:
			final = self.quota / final # Get the exact percentage from quota
			final = self.possible / final # Get the final exact percentage
						
			if final < self.possible:
				# We can safely update the progressbar.
				GObject.idle_add(self.progress_bar.set_fraction, self.current + final)
			else:
				# Assume we reached the maximum.
				GObject.idle_add(self.progress_bar.set_fraction, self.current + self.possible)
		except:
			pass
	
	def progress_finish_percentage(self):
		""" Updates the progress bar to the maximum possible by the module. """
				
		self.current += self.possible
		GObject.idle_add(self.progress_bar.set_fraction, self.current)
		
	
	def on_frontend_change(self):
		""" Focus on the frontend of the current module. """
		
		# Check if the frontend is glade (or a derivative), otherwise it's useless ;-)
		if "glade" in self.main_settings["frontend"]:
			if not self.pages_built:
				# We should wait until the pages are built
				while not self.pages_built:
					time.sleep(0.3)
						
			self.current_frontend.objects = self.modules_objects[self.current_module.package.replace("linstaller.modules.","")]
			
			m.handle_exception(self.current_frontend.on_objects_ready_internal)
			m.handle_exception(self.current_frontend.on_objects_ready)
			
			# Set header now.
			self.set_header("info",
							self.current_frontend.header_title,
							self.current_frontend.header_subtitle,
							self.current_frontend.header_icon
			)
			
			
			GObject.idle_add(m.handle_exception, self.current_frontend.pre_ready)
			GObject.idle_add(m.handle_exception, self.current_frontend.ready)
			
			# Set sensitivity, the frontend is up and running
			#GObject.idle_add(self.main.set_sensitive, True)
			
			GObject.idle_add(self.current_frontend.process)
			self.hide_spinner()
			#GObject.idle_add(self.header_eventbox.show)
	
	def build_pages(self, single=None, replacepage=None, onsuccess=None, newlocale=None):
		""" Searches for support glade files and adds them to the pages object.
		
		If single is a string, only the module matching that string will be builded.
		If replacepage is an int, the single page will be positioned to the argument's value, removing the old page.
		If onsuccess is True (and in single mode), the supplied method will be called when the pages have been built.
		
		Note that the single mode does work ONLY on the supplied module, other modules are not touched."""
		
		if newlocale:
			os.environ["LANG"] = newlocale
			os.environ["LC_ALL"]= newlocale
			
			import linstaller.core.changelocale as _cl
			_cl.change(newlocale)
			#locale.setlocale(locale.LC_ALL, newlocale)
			
			global _
			_ = t9n.library.translation_init("linstaller")
						
			# Reset title
			GObject.idle_add(self.main.set_title, _("%s Installer") % self.main_settings["distro"])

		if not replacepage and not single:
			self.modules_objects = {}
			self.inst_modules = []

		if replacepage and not single:
			current_page = self.pages.get_current_page()
			counter = -1
		
		# Get modules
		modules = self.main_settings["modules"]
		
		# Following the format introduced with linstaller 3.0 alpha 1, the modules are residing in directories (so welcome.front is welcome/front/ and not welcome/front.py)
		# Some modules may have not been converted to the new format, and we should handle them too.
		
		# GLADE FRONTEND WILL BE SEARCHED IN welcome/front/glade/ AND NOT in welcome/front/glade.py!
		
		for module in modules:
			if single and single != module: continue
			if module.split(".")[-1] == "inst":
				is_inst = True
			else:
				is_inst = False
			
			if module.startswith("!") or module.startswith("+"):
				# supermodule revert, skipping
				continue
			
			module_new = module.replace(".","/")
			module_new = os.path.join(MODULESDIR, module_new + "/glade/module.glade")
			
			if not os.path.exists(module_new) and not is_inst:
				warn(_("Module path %s does not exist! Skipping...") % module_new)
				continue
						
			objects_list = {"parent":self}
			
			if is_inst:
				# Inst module, skipping from now but adding to self.inst_modules...
				if not replacepage:
					self.modules_objects[module] = objects_list
					
					if os.path.exists(os.path.dirname(module_new)):
						self.inst_modules.append(module)
				continue
			
			# New builder
			objects_list["builder"] = Gtk.Builder()
			objects_list["builder"].set_translation_domain("linstaller")
			objects_list["builder"].add_from_file(module_new)
			
			# Get main object
			objects_list["main"] = objects_list["builder"].get_object("main")
			objects_list["main"].get_parent().remove(objects_list["main"])
			objects_list["main"].show_all()
			
			# Add to pages
			if single and replacepage:
				# Due to some Gtk.Notebook wierdness, the calling module MUST destroy the old main container.
				
				self.pages.insert_page(objects_list["main"], None, replacepage)
				
				# Also enter into the new page
				self.pages.set_current_page(replacepage)
			elif replacepage:
				counter +=1
				if counter > self.pages.get_current_page():
					if module in self.modules_objects:
						self.modules_objects[module]["main"].destroy()
					self.pages.remove_page(counter)
					self.pages.insert_page(objects_list["main"], None, counter)
				else:
					continue				
			else:
				self.pages.append_page(objects_list["main"], None)
			#self.pages.next_page()
			#self.pages.get_current_page()
			
			# Add to modules_objects
			self.modules_objects[module] = objects_list
			
		if single and onsuccess:
			onsuccess(objects_list)
			
		if not single and replacepage:
			self.pages.set_current_page(current_page)

	def get_module_object(self, module):
		""" Returns a module object for 'module'. """
		
		return self.modules_objects[module]
	
	def GUI_init(self):
		""" Get objects, show things... """
		
		self.pages_built = False
		
		self.is_fullscreen = False
		self.notifications_enabled = False
		
		self.builder = Gtk.Builder()
		self.builder.set_translation_domain("linstaller")
		self.builder.add_from_file(uipath)
		
		### EXIT WINDOW
		self.exitw = self.builder.get_object("exit")
		self.exitw.connect("delete_event", self.exitw_hide)
		
		self.exitw_yes = self.builder.get_object("exit_yes")
		self.exitw_yes.connect("clicked", self.please_exit)
		self.exitw_no = self.builder.get_object("exit_no")
		self.exitw_no.connect("clicked", self.exitw_hide)
				
		### MAIN WINDOW
		self.main = self.builder.get_object("main_window")
		self.main.connect("delete_event", self.exitw_show)
		
		self.box = self.builder.get_object("box")
		self.inst = self.builder.get_object("inst")
		
		self.buttons_area = self.builder.get_object("buttons_area")
		
		### HEADER
		#self.header_eventbox = Gtk.EventBox()
		self.header_eventbox = self.builder.get_object("header_eventbox")
		
		#self.header = Gtk.HBox()
		#self.header.set_homogeneous(False)
		#self.header_icon = Gtk.Image()
		#self.header_message_container = Gtk.VBox()
		#self.header_message_title = Gtk.Label()
		#self.header_message_subtitle = Gtk.Label()

		#self.header_message_container.pack_start(self.header_message_title, True, True, 0)
		#self.header_message_container.pack_start(self.header_message_subtitle, True, True, 0)
		
		#self.header.pack_start(self.header_icon, True, True, 0)
		#self.header.pack_start(self.header_message_container, True, True, 0)

		self.header_alignment = self.builder.get_object("header_alignment")

		self.header = self.builder.get_object("header")
		self.header_icon = self.builder.get_object("header_icon")
		self.header_message_container = self.builder.get_object("header_message_container")
		self.header_message_title = self.builder.get_object("header_message_title")
		self.header_message_subtitle = self.builder.get_object("header_message_subtitle")
		#self.header_alignment.reparent(self.header_eventbox)
		#self.header_eventbox.add(self.header)
		
		self.status_icon = self.builder.get_object("status_icon")
		
		self.box.pack_start(self.header_eventbox, True, True, 0)
		self.box.reorder_child(self.header_eventbox, 0)
		
		### PROGRESSBAR
		self.progress_label = self.builder.get_object("progress_label")
		self.progress_bar = self.builder.get_object("progress_bar")
				
		### PAGES
		self.pages_loading = self.builder.get_object("pages_loading")
		self.pages = self.builder.get_object("pages")
		
		self.next_button = self.builder.get_object("next_button")
		self.back_button = self.builder.get_object("back_button")
		self.cancel_button = self.builder.get_object("cancel_button")
		self.next_handler = self.next_button.connect("clicked", self.on_next_button_click)
		self.back_handler = self.back_button.connect("clicked", self.on_back_button_click)
		self.cancel_handler = self.cancel_button.connect("clicked", self.on_cancel_button_click)
		
		
		# Set back button as unsensitive, as we're in the first page
		GObject.idle_add(self.back_button.set_sensitive, False)

		# Header is a "toolbar"
		self.header_eventbox.get_style_context().add_class("toolbar")
		
		# Set title
		GObject.idle_add(self.main.set_title, _("%s Installer") % self.main_settings["distro"])
		
		self.build_pages()
		self.pages_built = True
		
		GObject.idle_add(self.pages_loading.hide)
		GObject.idle_add(self.main.show_all)

		# Hide inst
		GObject.idle_add(self.inst.hide)

		#self.main.set_resizable(True)
		#self.main.fullscreen()
			
	def fullscreen(self):
		""" Makes the window fullscreen. """
		
		if not self.is_fullscreen:
			GObject.idle_add(self.main.set_resizable, True)
			GObject.idle_add(self.main.fullscreen)
			self.is_fullscreen = True
	
	def unfullscreen(self):
		""" Unfullscreens the window """
		
		if self.is_fullscreen:
			GObject.idle_add(self.main.set_resizable, False)
			GObject.idle_add(self.main.unfullscreen)
			self.is_fullscreen = False
	
	def enable_notifications(self):
		""" Enables the notifications. """
		
		try:
			notify2.init("linstaller")
			self.notification = notify2.Notification(_("%s Installer") % self.main_settings["distro"],
													"linstaller is awesome <3",
													"info"   # Icon name
			)
			
			self.notifications_enabled = True
		except:
			# If we can't enable notifications, almost no one cares.
			# It's better to not have notifications than to have the
			# (in)famous drunk dialog! ;)
			self.notifications_enabled = False
	
	def update_and_show_notification(self, message, icon=None):
		""" Updates and shows the notification. """
		
		if not self.notifications_enabled: return
		
		self.notification.message = message
		if icon: self.notification.icon = icon
		try:
			if not self.main.is_active():
				self.notification.show()
			else:
				# We need to ensure that the notification is closed to
				# avoid displaying not up-to-date infos when an action
				# has been a triggered by another window (e.g: partdisks'
				# Apply dialog).
				self.notification.close()
		except:
			# In some cases, a DBusException is raised randomly.
			# We do not want that.
			pass

	def set_header(self, icon, title, subtitle, appicon=None, toolbarinfo=True):
		""" Sets the header with the delcared icon, title and subtitle. """

		if icon == "info":
			# Header: title, Status: subtitle
			GObject.idle_add(self.header_message_title.set_markup, title.replace("& ", "&amp; "))
			GObject.idle_add(self.header_message_subtitle.set_markup, subtitle)
			
			# Icon: appicon (if any), Status icon: info
			if not appicon:
				appicon = head_ico[icon]

			GObject.idle_add(self.header_icon.set_from_icon_name, appicon, 6)
			# Reset tooltip
			GObject.idle_add(self.header_message_subtitle.set_tooltip_text, None)
			GObject.idle_add(self.status_icon.set_tooltip_text, None)

			self.update_and_show_notification(title, appicon)

		else:
			# Change only subtitle (and set title there)
			GObject.idle_add(self.header_message_subtitle.set_markup, "<span color=\"%s\">%s</span>" % (head_col[icon], title))
			# Set the subtitle as the tooltip
			GObject.idle_add(self.header_message_subtitle.set_tooltip_text, subtitle)
			GObject.idle_add(self.status_icon.set_tooltip_text, subtitle)
			
			self.update_and_show_notification(title)
		
		GObject.idle_add(self.status_icon.set_from_icon_name, head_ico[icon], 2)

	def change_entry_status(self, obj, status, tooltip=None):
		""" Changes entry secondary icon for object. """
				
		GObject.idle_add(obj.set_icon_from_icon_name, Gtk.EntryIconPosition.SECONDARY, head_ico[status])
		GObject.idle_add(obj.set_icon_tooltip_text, Gtk.EntryIconPosition.SECONDARY, tooltip)

	def exitw_show(self, obj=None, thing=None):
		""" Shows the exit dialog. """
		
		# If on_inst, do not show anything ;)
		if self.on_inst:
			return True
		
		self.main.set_sensitive(False)
		self.exitw.show()
		
		return True
	
	def exitw_hide(self, obj=None, thing=None):
		""" Hides the exit dialog. """
		
		self.main.set_sensitive(True)
		self.exitw.hide()
		
		return True

	def please_exit(self, obj):
		""" Executed when the main window is destroyed. """
		
		self.current_frontend.end()

	def on_cancel_button_click(self, obj):
		""" Executed when the Cancel button is clicked. """
		
		self.exitw_show()

	def show_spinner(self):
		""" Shows the spinner. """
		
		GObject.idle_add(self.buttons_area.set_sensitive, False)
		GObject.idle_add(self.header_eventbox.hide)
		GObject.idle_add(self.pages.hide)
		GObject.idle_add(self.pages_loading.show)
	
	def hide_spinner(self):
		""" Reverts the changes done by show_spinner(). """

		GObject.idle_add(self.buttons_area.set_sensitive, True)
		GObject.idle_add(self.header_eventbox.show)
		GObject.idle_add(self.pages.show)
		GObject.idle_add(self.pages_loading.hide)

	def on_next_button_click(self, obj=None):
		""" Executed when the Next button is clicked. """

		if self.current_frontend.on_next_button_click() != None:
			return
		
		# Do on_module_change
		self.current_frontend.on_module_change()
		
		# Make sure everything is not sensitive until the frontend is up and running
		#if not self.on_inst: GObject.idle_add(self.main.set_sensitive, False)
		#self.set_header("info", "Loading...", "Loading.")
		if not self.on_inst: self.show_spinner()
				
		GObject.idle_add(self.next_module)
		if not self.on_inst: GObject.idle_add(self.pages.next_page)
		
		# Ensure the back button is clickable
		if not self.on_inst: GObject.idle_add(self.back_button.set_sensitive, True)
	
	def on_back_button_click(self, obj=None):
		""" Executed when the Back button is clicked. """

		if self.current_frontend.on_back_button_click() != None:
			return

		# Do on_module_change
		self.current_frontend.on_module_change()

		# Make sure everything is not sensitive until the frontend is up and running
		#if not self.on_inst: GObject.idle_add(self.main.set_sensitive, False)
		if not self.on_inst: self.show_spinner()
		
		GObject.idle_add(self.prev_module)
		if not self.on_inst: GObject.idle_add(self.pages.prev_page)
		
		# If this is the first page, make unsensitive the button.
		if not self.on_inst and self.pages.get_current_page() in (0, -1):
			GObject.idle_add(self.back_button.set_sensitive, False)

	def change_next_button_to_reboot_button(self):
		""" Changes the next button to a reboot button. """
		
		GObject.idle_add(self.next_button.set_label, _("Reboot"))
		GObject.idle_add(self.next_button.disconnect, self.next_handler)
		
		# Using idle_add to do the following will make linstaller's RAM
		# usage grow infinitely...
		self.next_button.connect("clicked", self.kthxbye)

	def change_next_button_to_fullrestart_button(self):
		""" Changes the next button to a fullrestart button. """
		
		GObject.idle_add(self.next_button.set_label, _("Restart installer"))
		GObject.idle_add(self.next_button.disconnect, self.next_handler)
		
		# Using idle_add to do the following will make linstaller's RAM
		# usage grow infinitely...
		self.next_button.connect("clicked", self.fullrestart)

	def on_caspered(self, status):
		""" Override on_caspered to make sure we handle correctly back/forward jobs when a module has been caspered. """
		
		if status == None:
			# Forward
			# Make sure everything is not sensitive until the frontend is up and running
			if not self.on_inst:
				self.show_spinner()
				GObject.idle_add(self.pages.next_page)
				self.hide_spinner()
							
				# Ensure the back button is clickable
				GObject.idle_add(self.back_button.set_sensitive, True)
		elif status == "back":
			# Back
			# Make sure everything is not sensitive until the frontend is up and running
			if not self.on_inst:
				self.show_spinner()
				GObject.idle_add(self.pages.prev_page)
				self.hide_spinner()
			
				# If this is the first page, make unsensitive the button.
				if not self.on_inst and self.pages.get_current_page() in (0, -1):
					GObject.idle_add(self.back_button.set_sensitive, False)

	def ready(self):
		
		# Check if the frontend is glade (or a derivative), otherwise it's useless ;-)
		if "glade" in self.main_settings["frontend"]:
			self.GUI_init()	
	
	def run(self):
		# Check if the frontend is glade (or a derivative), otherwise it's useless ;-)
		
		if "glade" in self.main_settings["frontend"]:
			Gtk.main()
		else:
			verbose("""################################################################################################
Welcome to the next episode of "How wasting CPU cycles and memory"!
This episode is about Services. Oh yes, this service is running on a separate thread but nothing
requires it. The frontend, in fact, is %s and not glade.

Therefore, is advised to disable the "glade" service. The Gtk main loop will not be started and
nothing bad will happen. This message is just to let you know.

If you are a normal user and not a developer, do not worry. You should be happy that you found
this easter egg!
################################################################################################
""" % self.main_settings["frontend"])
		
	def on_close(self):
		""" Triggered when linstaller needs to close shop. """

		# Check if the frontend is glade (or a derivative), otherwise it's useless ;-)
		if "glade" in self.main_settings["frontend"]:
			self.main.hide()
			Gtk.main_quit()
