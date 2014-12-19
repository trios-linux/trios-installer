# -*- coding: utf-8 -*-
# linstaller partdisks module frontend - (C) 2011-12 Eugenio "g7" Paolantonio and the Semplice Team.
# All rights reserved. Work released under the GNU GPL license, version 3 or later.
#
# This is a module of linstaller, should not be executed as a standalone application.

import linstaller.frontends.cli as cli
import linstaller.core.main as m
import copy
import t9n.library
_ = t9n.library.translation_init("linstaller")

from linstaller.core.main import warn,info,verbose,bold

import linstaller.core.libmodules.partdisks.library as lib

class Frontend(cli.Frontend):
	def start(self):
		""" Start the frontend """
		
		self.onlyusb = False

		# Cache distribs
		self.distribs = lib.check_distributions()

		#self.devices, self.disks = lib.return_devices() # Obtain devices
		self.devices, self.disks = lib.devices, lib.disks

		if self.settings["onlyusb"]:
			self.onlyusb = True # Keep track of onlyusb
			# Only usb, we need to rebuild devices.
			lib.restore_devices(onlyusb=True)

		self.touched = {}
		self.changed = {}

		self.main()
	
	def main(self):
		""" Main prompt. """

		self._reload(complete=False)
		self.header(_("Disk partitioning"))

		# Check if root and swap are preseeded.
		if self.settings["root"] and self.settings["swap"] != False:
			# They are. We can skip this step.
			
			## ROOT
			
			# Get an appropriate device object
			_root_dev = self.disks[lib.return_device(self.settings["root"]).replace("/dev/","")]
			# Get an appropriate partition object
			_root_par = _root_dev.getPartitionByPath(self.settings["root"])
			
			self.changed[self.settings["root"]] = {"obj":_root_par, "changes":{"useas":"/"}}
			###################################################################################
			
			## SWAP
			
			# Get an appropriate device object
			if not self.settings["swap"]:
				# Swap disabled
				self.settings["swap_noformat"] = True # Do not format swap, as it doesn't exist ;)
			else:
				# Get an appropriate partition object
				_swap_dev = self.disks[lib.return_device(self.settings["swap"]).replace("/dev/","")]
				_swap_par = _swap_dev.getPartitionByPath(self.settings["swap"])
				
				self.changed[self.settings["swap"]] = {"obj":_swap_par, "changes":{"useas":"swap"}}
			#######################################################################################
						
			# If root_filesystem is populated, we should format root with that filesystem.
			if self.settings["root_filesystem"]:
				# Format. Yay.
				# Set format.
				self.changed[self.settings["root"]]["changes"]["format"] = self.settings["root_filesystem"]
				self.changed[self.settings["root"]]["changes"]["format_real"] = self.settings["root_filesystem"]
				self.touched[lib.return_device(self.settings["root"])] = True
			
			if not self.settings["swap_noformat"]:
				# Format. Yay.
				# Set format.
				self.changed[self.settings["swap"]]["changes"]["format"] = "linux-swap(v1)"
				self.changed[self.settings["swap"]]["changes"]["format_real"] = "linux-swap(v1)"
				self.touched[lib.return_device(self.settings["swap"])] = True
			
			# Write to memory
			lib.write_memory(self.changed)
			
			# Commit.
			self.commit()

			verbose("Selected %s as root partition" % self.settings["root"])
			if self.settings["swap"]:
				verbose("Selected %s as swap partition" % self.settings["swap"])
			else:
				verbose("Swap disabled.")

			# Skip to next module
			return
		
		# If skip_to_selection == True, we need to skip the following block.
		if self.settings["skip_to_selection"] != True:
			self.print_devices_partitions()
			
			res = self.question(_("Do you want to change the partition table?"), default=False)
			if res:
				# We should change partition structure.
				res = self.edit_partitions()
				# Restart this module
				return self.main()
			else:
				# Check if root and swap are preseeded.
				self.partition_selection()
		else:
			# Run partition_selction()
			self.partition_selection()
			
		verbose("Selected %s as root partition" % self.settings["root"])
		if self.settings["swap"]:
			verbose("Selected %s as swap partition" % self.settings["swap"])
		else:
			verbose("Swap disabled.")
		
		verbose("Other changes: %s" % str(self.changed))
			
	def partition_selection(self, warning=None, information=None):
		""" If root and swap aren't preseeded, prompts the user for a partition. """
		
		self.header(_("Select distribution specific drives"))
		
		if warning:
			warn(warning + "\n")
		if information:
			info(information + "\n")
		
		self.print_devices_partitions()
		
		if not self.settings["root"]:
			# No root specified. Prompt for one.
			choice = self.entry(_("Select your root partition"))
			# Check if choice is into disk's partition
			try:
				_root_dev = self.disks[lib.return_device(choice).replace("/dev/","")]
				_root_par = _root_dev.getPartitionByPath(choice)
				if not _root_par:
					# Wrong disk
					return self.partition_selection(warning=_("Wrong partition selected!"))
			except:
				# Wrong disk
				return self.partition_selection(warning=_("Wrong partition selected!"))
			
			self.changed[choice] = {"obj":_root_par, "changes":{"useas":"/"}}
			self.settings["root"] = choice
			
			if not self.settings["root_filesystem"] and not self.settings["root_noformat"]:
				# No filesystem for root specified.
				# Prompt for one.
				
				return self.edit_partitions_format(_root_par, self.changed[choice]["changes"], _return="partsel")
			elif not self.settings["root_noformat"]:
				self.changed[choice]["changes"]["format"] = self.settings["root_filesystem"]
				self.changed[choice]["changes"]["format_real"] = self.settings["root_filesystem"]
				self.touched[lib.return_device(choice)] = True

		if self.settings["swap"] == False:
			
			swaps = lib.swap_available(deep=True)
			if swaps == []:
				# No swap available
				warn(_("No swap partition available. Continuing without."))
				self.settings["swap"] = None
			else:
				# No swap specified. Prompt for one.
				choice = self.entry(_("Select your swap partition (press ENTER to not use swap)"), blank=True)
				if not choice:
					# Should not use swap. ok...
					self.settings["swap"] = None
					warn(_("No swap selected."))
				else:
					# Check if choice is into disk's partition
					_swap_par = False
					for part in swaps:
						if choice == part.path:
							_swap_par = part
					
					if not _swap_par:
						# No swap :/
						return self.partition_selection(warning=_("Wrong partition selected!"))
					
					self.changed[choice] = {"obj":_swap_par, "changes":{"useas":"swap"}}
					self.settings["swap"] = choice
					
					if not self.settings["swap_noformat"]:
						# Prompt for format.
						
						# Set format.
						self.changed[choice]["changes"]["format"] = "linux-swap(v1)"
						self.changed[choice]["changes"]["format_real"] = "linux-swap(v1)"
						self.touched[lib.return_device(self.settings["swap"])] = True
		
		if self.settings["root_noformat"]:
			# Do not alarm the user that we are going to format something -- as we will not format anything (if not swap)
			quest = _("Do you really want to continue?")
		else:
			quest = _("Do you really want to continue? This will destroy selected partitions.")
		
		res = self.question("\n" + quest, default=False)
		if res:	
			# Write to memory
			lib.write_memory(self.changed)
			
			# Commit.
			self.commit()
			
			return
		else:
			return self.main()

	
	def _reload(self, interactive=False, complete=True):
		""" Reloads original structure. """
		
		if interactive:
			self.header(_("Reload original table"))
			
			print(_("This will reload the original partition table."))
			print(_("All changes you've done will be lost.") + "\n")
			
			res = self.question(_("Do you want to continue?"), default=False)
			if not res:
				return self.edit_partitions()
		
		# Reload.
		lib.restore_devices(onlyusb=self.onlyusb)
		self.disks, self.devices = lib.disks, lib.devices
		
		# Remove touched
		self.touched.clear()
		
		# Also remove flags.
		for name, changes in self.changed.items():
			if complete:
				# Clear.
				changes["changes"].clear()
			else:
				# Remove all but useas
				for key, value in changes["changes"].items():
					if not key == "useas":
						del changes["changes"][key]

		if interactive:
			return self.edit_partitions()
	
	def back(self):
		""" Goes back. """
		
		if not self.touched == {}:
			self.header(_("Go back"))
			
			print(_("It appears that you have uncommited changes to the partitioning scheme."))
			print(_("If you want to commit them, you need first to write to memory the changes and then to commit."))
			print(_("To do so, you should go to the 'edit partitions' page and select the relative options.") + "\n")
			
			res = self.question(_("Do you really want to go back without saving changes?"), default=False)
			if not res:
				return self.edit_partitions()
		
		return
	
	def commit(self, interactive=False):
		""" Commits all the changes to the disks. """
		
		if interactive:
		
			self.header(_("Commit changes"))
			
			print(_("This table is going to be applied:"))
			print
			
			self.print_devices_partitions()
			
			print
			
			print(_("%(warning)s: This will COMMIT ALL THE CHANGES YOU'VE DONE on the physical disks.") % {"warning":bold(_("WARNING"))})
			print(_("This is the last time that you can check your new partition table."))
			print(_("If you continue, you CAN'T RESTORE THE OLD TABLE!") + "\n")
			
			result = self.question(_("Do you really want to continue?"), default=False)
		else:
			result = True

		if result:
			# Ok, continue.
			lst, dct = lib.device_sort(self.changed)
			for key in lst:
				try:
					obj = dct[key]["obj"]
					cng = dct[key]["changes"]
				except:
					verbose("Unable to get a correct object/changes from %s." % key)
					continue # Skip.
								
				verbose("Committing changes in %s" % key)
				
				# If working in a Virtual freespace partition, pyparted will segfault.
				# The following is a workaround, but should be fixed shortly.
				#                FIXME
				#           FIXME     FIXME
				#      FIXME    ______     FIXME
				# FIXME        |      |         FIXME
				# FIXME        |      |               FIXME
				# FIXME FIXME FIXME FIXME FIXME FIXME FIXME
				# ------------------------------------------
				# Figure 1: A FIXME big like an house.
				if "-1" in key:
					continue				

				# New partition table?
				if "newtable" in cng:
					progress = lib.new_table(obj, cng["newtable"])
					info(_("Creating new partition table on %s...") % key)
					status = progress.wait()
					if status != 0:
						# Failed ...
						if interactive:
							return self.edit_partitions(warning=_("FAILED: new partition table in %s") % key)
						else:
							raise m.CmdError(_("FAILED: new partition table in %s") % key)
					
					# Clear touched, as only this action can be done if we do not own a disk.
					del self.touched[obj.path]


				# Commit on the disk.
				lib.commit(obj, self.touched)
								
				# Should format?
				if "format_real" in cng:
					# If this is going to be the swap partition, if swap_nofromat is setted, we should not format.
					#if "useas" in cng and cng["useas"] == "swap" and self.settings["swap_noformat"]:
					#	continue
					# Yes.
					progress = lib.format_partition_for_real(obj, cng["format_real"])
					info(_("Formatting %s...") % key)
					status = progress.wait()
					if status != 0:
						# Failed ...
						if interactive:
							return self.edit_partitions(warning=_("FAILED: formatting %s") % key)
						else:
							raise m.CmdError(_("FAILED: formatting %s") % key)
								
				# Check if it is root or swap
				if "useas" in cng:
					if cng["useas"] == "/":
						# Preseed
						self.settings["root"] = key
						self.settings["root_noformat"] = True
					elif cng["useas"] == "swap":
						# Preseed
						self.settings["swap"] = key
						self.settings["swap_noformat"] = True
				
		# Preseed *all* changes
		self.settings["changed"] = self.changed
		
		# Reload.
		self._reload(complete=False) # Preserve useas.
		
		# Return.
		if interactive: return self.edit_partitions()
			
	
	def edit_partitions(self, warning=None, information=None, device=False, device_changes=False):
		""" Partition editor. """
		
		self.header(_("Edit Partition structure"))
		if warning:
			warn(warning + "\n")
		if information:
			info(information + "\n")
		
		res, choices = self.print_devices_partitions(interactive=True)
		try:
			res = int(res)
		except ValueError:
			return self.edit_partitions(warning=_("You didn't entered a valid number."))
		
		if not res in choices:
			# Number doesn't is in choices.
			return self.edit_partitions(warning=_("You didn't entered a valid number."))
		
		# We can continue.

		obj = choices[res]
		if obj == "back": return self.back() # We should go back.
		if obj == "write": return self.edit_partitions_write() # We should write to disk.
		if obj == "automatic": return self.automatic() # Automatic partitioning.
		if obj == "reload": return self._reload(interactive=True) # Reload.
		if obj == "commit": return self.commit(interactive=True) # Commit.
		self.header(_("Editing disk/partition"))
		
		print(_("You've selected:") + "\n")
		if type(obj) == lib.p.partition.Partition:
			
			if obj.fileSystem == None and not obj.number == -1 and not obj.type == 2:
				# If filesystem == None, skip.
				_fs = _("not formatted")
			elif obj.number == -1:
				_fs = _("free space")
			elif obj.type == 2:
				# Extended objition
				_fs = _("extended")
			else:
				_fs = obj.fileSystem.type

			if obj.name:
				_name = obj.name
			else:
				_name = "Untitled"

			if obj.path in self.distribs:
				# This partition contains a distribution!
				_moarspace = "%s: " % self.distribs[obj.path]
			else:
				_moarspace = ""
			
			if int(obj.getSize("GB")) > 0:
				# We can use GigaBytes to represent partition size.
				_size = round(obj.getSize("GB"), 2)
				_unit = "GB"
			elif int(obj.getSize("MB")) > 0:
				# Partition is too small to be represented with gigabytes. Use megabytes instead.
				_size = round(obj.getSize("MB"), 2)
				_unit = "MB"
			else:
				# Last try.. using kilobytes
				_size = round(obj.getSize("kB"), 2)
				_unit = "kB"

			print(bold("   %s%s (%s) - %s (%s %s)\n" % (_moarspace, _name, obj.path, _fs, _size, _unit)))
			
			actions = {}
			# Populate actions
			if obj.number == -1:
				actions[1] = (_("Add partition"), self.edit_partitions_add)
				num = 1
			else:
				actions[1] = (_("Format partition"), self.edit_partitions_format)
				actions[2] = (_("Delete partition"), self.edit_partitions_delete)
				actions[3] = (_("Resize partition"), self.edit_partitions_resize)
				actions[4] = (_("Use as..."), self.edit_partitions_useas)
				actions[5] = (_("Unmark changes"), self.edit_partitions_unmark)
				num = 5
			
			actions[num + 1] = (_("<- Back"), self.edit_partitions)
		
		elif type(obj) == lib.p.disk.Disk:
			# A disk.
			
			device = obj.device
			
			print("   %s - %s (%s GB)\n" % (device.path, device.model, round(device.getSize(unit="GB"), 2)))
			
			actions = {}
			# Populate actions
			actions[1] = (_("Delete all partitions on the disk"), self.edit_partitions_deleteall)
			actions[2] = (_("Unmark changes"), self.edit_partitions_unmark)
			actions[3] = (_("<- Back"), self.edit_partitions)
		else:
			# A device.
			
			device = obj
			
			print("   %s - %s (%s GB)\n" % (device.path, device.model, round(device.getSize(unit="GB"), 2)))
			
			actions = {}
			# Populate actions
			actions[1] = (_("Create MBR partition table"), self.edit_partitions_newmbr)
			actions[2] = (_("Create GPT partition table"), self.edit_partitions_newgpt)
			actions[3] = (_("<- Back"), self.edit_partitions)
		
		# Print actions
		for num, act in actions.iteritems():
			print(" %d) %s") % (num, act[0])
		print
			
		result = self.entry(_("Please insert your action here"))
		try:
			result = int(result)
		except:
			return self.edit_partitions(warning=_("You didn't entered a valid action."))
		if not result in actions:
			return self.edit_partitions(warning=_("You didn't entered a valid action."))
		
		# Generate a new device_changes, if any
		if type(obj) == lib.p.disk.Disk:
			# It is a Disk object, we should use Disk.device
			_path = obj.device.path
		else:
			_path = obj.path
		
		if not _path in self.changed:
			self.changed[_path] = {"obj":obj, "changes":{}}
		
		return actions[result][1](device=obj, device_changes=self.changed[_path]["changes"])
	
	def automatic(self, warning=False, information=False, jumpto=False, by="freespace"):
		""" Automatic partitioner. That's cool, babe! """
		
		self.header(_("Automatic partitioner"))

		if warning:
			warn(warning + "\n")
		if information:
			info(information + "\n")

		# *RELOAD* original structure
		self._reload()


		if not jumpto:
			print(_("Available disks:"))
			res, choices = self.print_devices_partitions(interactive=True, only_disks=True, skip_notable=True)
			try:
				res = int(res)
			except ValueError:
				return self.edit_partitions(warning=_("You didn't entered a valid number."))
			
			if not res in choices:
				# Number doesn't is in choices.
				return self.edit_partitions(warning=_("You didn't entered a valid number."))
			
			obj = choices[res]
			if obj == "back": return self.edit_partitions() # Go back.
			
			self.header(_("Automatic partitioner") + " - %s" % obj.device.path)
			
			actions = {}
			actions[0] = (_("Use the free space"), "freespace")
			actions[1] = (_("Delete another system"), "delete")
			actions[2] = (_("Delete all partitions"), "deleteall")
			actions[3] = (_("Back"), "back")
			
			# Print actions
			for num, act in actions.iteritems():
				print(" %d) %s") % (num, act[0])
			print
				
			result = self.entry(_("Please insert your action here"))
			try:
				result = int(result)
			except:
				return self.edit_partitions(warning=_("You haven't entered a valid action."))
			if not result in actions:
				return self.edit_partitions(warning=_("You haven't entered a valid action."))
	
			by = actions[result][1]

			if by == "back": return self.edit_partitions() # Go back.
		
		if jumpto: obj = jumpto

		# We can continue.
		if by == "freespace":
			part, swap, swapcreated = lib.automatic_check(obj, by=by)
			if part == None:
				return self.automatic(information=_("Too little free space"))
			elif part == False:
				# Failed.
				return self.automatic(warning=_("Failed to add partition (AUTOMATIC)"))
			else:
				# Yey!
				
				self.header(_("Automatic partitioner choices"))
				
				if swap:
					# Get swap size.
					if int(swap.getSize("GB")) == 0:
						# GB is too big, use MB instead.
						_swap_unit = "MB"
						_swap_size = round(swap.getSize("MB"))
					else:
						# We can use GB.
						_swap_unit = "GB"
						_swap_size = round(swap.getSize("GB"))
				
				# Set-up touched...
				self.touched[part.path] = True
				if swap: self.touched[swap.path] = True
				
				print("   / - %s (%s - %s GB)" % (part.path, part.fileSystem.type, round(part.getSize("GB"), 2)))
				if swap: print("   swap - %s (%s %s)" % (swap.path, _swap_size, _swap_unit))
		elif by == "delete":
			delete, swap = lib.automatic_check(obj, by=by)
			swapcreated = False
			
			print delete
			if not delete:
				# No distribution to delete.
				return self.automatic(warning=_("No distribution to delete!"))
			else:
				# Yey!
				
				self.header(_("Automatic partitioner choices"))
				
				if swap:
					# Get swap size.
					if int(swap.getSize("GB")) == 0:
						# GB is too big, use MB instead.
						_swap_unit = "MB"
						_swap_size = round(swap.getSize("MB"))
					else:
						# We can use GB.
						_swap_unit = "GB"
						_swap_size = round(swap.getSize("GB"))
				
				actions = {}
				num = 0
				for part, distrib in delete:
					actions[num] = part
					print("   %s) (%s) / - %s (%s - %s GB)" % (num, bold(distrib), part.path, part.fileSystem.type, round(part.getSize("GB"), 2)))
					num += 1
				print
				print("   %s) " % num + _("<- Back"))
				actions[num] = "back"
				print

				if swap:
					print(_("Whatever will be the selection, this swap partition will be used:") + "\n")
					print("   swap - %s (%s %s)" % (swap.path, _swap_size, _swap_unit))
					print
				else:
					# Swap will be created - hopefully - by freespace.
					print(_("A swap partition, if all conditions are meet, will be created."))
					print
				
				# Select action
				result = self.entry(_("Please insert your value here"))
				try:
					result = int(result)
				except:
					return self.automatic(warning=_("You didn't entered a valid value."))
				if not result in actions:
					return self.automatic(warning=_("You didn't entered a valid value."))
				
				if actions[result] == "back":
					# Go back.
					return self.automatic()
				
				# If we can continue, delete partition!!
				lib.delete_partition(actions[result])
				
				# Now there is freespace ;-)
				# So use "freespace".
				return self.automatic(jumpto=obj, by="freespace")
		elif by == "deleteall":
			# The simplest ever!
			
			lib.delete_all(obj)
			
			# Now there is freespace ;-)
			# So use "freespace".
			return self.automatic(jumpto=obj, by="freespace")
			
		print	
		res = self.question(_("Are you happy with this? Enter 'y' to write changes in memory"), default=True)

		# Cache part in self.changed
		if not part.path in self.changed:
			self.changed[part.path] = {"obj":part, "changes":{}}

		# Cache swap in self.changed
		if swap:
			if not swap.path in self.changed:
				self.changed[swap.path] = {"obj":swap, "changes":{}}

		if res:			
			# Add useas.
			self.changed[part.path]["changes"] = {"useas":"/", "format_real":"ext4"}
			
			if swap: self.changed[swap.path]["changes"] = {"useas":"swap", "format_real":"linux-swap(v1)"}
		elif by == "freespace" and not jumpto:
			# We should deleted created partitions
			lib.delete_partition(part)
			if swapcreated: lib.delete_partition(swap) # We should delete swap if it was created.
		else:
			# We cannot undo, restore old structure
			self._reload()
			# Remove useas flags
			self.changed[part.path]["changes"] = {}
			if swap: self.changed[swap.path]["changes"] = {}
		
		return self.edit_partitions(information=_("Successfully added partitions."))
	
	def edit_partitions_add(self, device, device_changes):
		""" Adds a partition from the freespace. """
		
		self.header(_("Add a partition"))
		
		print(_("Current free space size: %s") % round(device.getSize("MB"), 3))
		print(_("You can insert the percentage of the partition (e.g: 50%) or the full size of the new partition, in MB.") + "\n")

		res = self.entry(_("Insert the value here [press ENTER to go back]"), blank=True)
		if not res:
			# pressed ENTER
			return self.edit_partitions()
			
		if "%" in res and res != "100%":
			# This is a percentage, folks!
			res = res[:-1] # Drop last %
			try:
				res = float(res)
			except:
				# Not a number
				return self.edit_partitions(warning=_("Wrong percentage specified!"))
			res = (res * device.getSize()) / 100.0
		elif res == "100%":
			res = device.geometry.length
		else:
			if float(res) == round(device.getSize("MB"), 3):
				# Full partition.
				res = device.getSize()
			else:
				try:
					res = lib.MbToSector(float(res))
				except:
					# Not a number
					return self.edit_partitions(warning=_("Wrong value specified!"))

		# Check if we can grow the partition at the given size...
		if device.getSize() < res:
			# No!
			return self.edit_partitions(warning=_("Not enough space!"))

		#_supported = lib.get_supported_filesystems()
		
		#print(_("Available Filesystems:") + "\n")
		#for fs in _supported.keys():
		#	print("  %s" % fs)
		#print
		
		#_request = _("Insert the filesystem you want to use here")
		#
		#_fs = self.entry(_request)
		#if not _fs in _supported:
		#	return self.edit_partitions(warning=_("%s is not a supported filesystem!") % _fs)
		
		# Write directly in memory...
		lib.add_partition(device.disk, start=device.geometry.start, size=res, type=lib.p.PARTITION_NORMAL, filesystem=None)
		#device_changes["format"] = _fs
		#device_changes["format_real"] = _fs
		self.touched[device.path] = True
		
		return self.edit_partitions(information=_("Done. Now add a filesystem to the partition."))
	
	def edit_partitions_deleteall(self, device, device_changes):
		""" Marks all partitions on the device to be deleted. """
		
		self.header(_("Delete all partitions"))
		
		# Mark as deleted, then return
		
		# Unmark all partitions in this disk...
		for part in device.partitions:
			self.changed[part.path]["changes"].clear()

		device_changes["deleteall"] = True
		self.touched[device.device.path] = True
		return self.edit_partitions(information=_("Changes marked succesfully. Now write the changes to memory."))

	def edit_partitions_newmbr(self, device, device_changes):
		""" Marks a device to be erased with a new MBR partition table. """
				
		device_changes["newtable"] = "mbr"
		self.touched[device.path] = True
		return self.edit_partitions(information=_("Changes marked succesfully. Please save changes."))

	def edit_partitions_newgpt(self, device, device_changes):
		""" Marks a device to be erased with a new MBR partition table. """
				
		device_changes["newtable"] = "gpt"
		self.touched[device.path] = True
		return self.edit_partitions(information=_("Changes marked succesfully. Please save changes."))

	def edit_partitions_format(self, device, device_changes, _return="edit"):
		""" Marks a partition to be formatted. """
		
		if _return == "edit":
			_return = self.edit_partitions
		else:
			_return = self.partition_selection
		
		if "delete" in device_changes:
			# Marked for deletion
			return self.edit_partitions(warning="Partition is already marked as deleted!")
		
		self.header(_("Format partition"))
		
		_supported = lib.get_supported_filesystems()
		
		print(_("Available Filesystems:") + "\n")
		for fs in _supported.keys():
			print("  %s" % fs)
		print
		
		_request = _("Insert the filesystem you want to use here")
		if "format" in device_changes:
			_request_update = " " + _("[press ENTER for '%s']") % device_changes["format"]
			_blank = True
		else:
			_request_update = ""
			_blank = False
		
		request = self.entry("%s%s" % (_request, _request_update), blank=_blank)
		if request:
			if not request in _supported:
				return _return(warning=_("%s is not a supported filesystem!") % request)
			# We can continue.
			device_changes["format"] = request
			device_changes["format_real"] = request
			self.touched[device.disk.device.path] = True
		
		return _return(information=_("Changes marked succesfully."))
	
	def edit_partitions_delete(self, device, device_changes):
		""" Marks a partition to be deleted """
		
		self.header(_("Delete partition"))
		if device.number == -1:
			return self.edit_partitions(warning=_("You can't delete freespace!"))
		
		# If the entire disk is marked as deleted, we should skip.
		if "deleteall" in self.changed[device.disk.device.path]["changes"]:
			# Skip.
			return self.edit_partitions(information=_("The disk containing this partitions is already marked as deleted."))
		
		# Clear, Mark as deleted, then return
		device_changes.clear() # Clear
		device_changes["delete"] = True
		self.touched[device.disk.device.path] = True
		return self.edit_partitions(information=_("Changes marked succesfully. Now write the changes in memory."))
	
	def edit_partitions_useas(self, device, device_changes):
		""" Marks a partition to be used as... (/, /home, etc) """
		
		self.header(_("Use as..."))
		if device.number == -1 or device.type == 2:
			return self.edit_partitions(warning=_("You can't execute this action on freespace or on an extended partition!"))
		
		print(_("Here you can insert the mount point of this partition."))
		print(_("For example, if you want to mount as /home, insert '/home'.") + "\n")
		
		_request = _("Insert the mountpoint here")
		if "useas" in device_changes:
			_request_update = " " + _("[press ENTER for '%s']") % device_changes["useas"]
			_blank = True
		else:
			_request_update = ""
			_blank = False
		
		request = self.entry("%s%s" % (_request, _request_update), blank=_blank)
		if request:
			if not "/" in request[0]:
				# Not / in mountpoint, is an error!
				return self.edit_partitions(warning=_("%s is not a valid mountpoint!") % request)
			# We can continue.
			device_changes["useas"] = request
		
		return self.edit_partitions(information=_("Changes marked succesfully."))
	
	def edit_partitions_resize(self, device, device_changes):
		""" Marks a partition to be resized. """
		
		self.header(_("Resize partition"))
		if device.number == -1 or device.type == 2:
			return self.edit_partitions(warning=_("You can't resize freespace or an extended partition!"))
		
		print(_("Current partition size: %s") % round(device.getSize("MB"), 3))
		print(_("You can insert the percentage of the resize (e.g: 50%) or the full size for the resized partition, in MB."))
		print(_("In order to make change to the free space that the resize operation will make, you will need to write in memory the changes.") + "\n")
		res = self.entry(_("Insert the value here [press ENTER to go back]"), blank=True)
		if not res:
			# pressed ENTER
			return self.edit_partitions()
		
		if "%" in res and res != "100%":
			# This is a percentage, folks!
			res = res[:-1] # Drop last %
			try:
				res = float(res)
			except:
				# Not a number
				return self.edit_partitions(warning=_("Wrong percentage specified!"))
			res = (res * device.getSize()) / 100.0
		elif res == "100%":
			return self.edit_partitions(warning=_("Partition is already at the given value!"))
		else:
			if float(res) == round(device.getSize("MB"), 3):
				# Full partition.
				return self.edit_partitions(warning=_("Partition is already at the given value!"))
			else:
				try:
					res = lib.MbToSector(float(res))
				except:
					# Not a number
					return self.edit_partitions(warning=_("Wrong value specified!"))
		
		# Check if we can grow the partition at the given size...
		#print device.getMaxGeometry().length
		print res
		print lib.MbToSector(device.getMaxAvailableSize())
		
		try:
			# Generate a new fake geometry
			_geom = lib.p.Geometry(device=device.disk.device, start=device.geometry.start, length=res)
			# Generate a new fake constraint
			_cons = lib.p.Constraint(exactGeom=_geom)
		except:
			# No!
			return self.edit_partitions(warning=_("Not enough space!"))
			
		
		# Add to changes
		device_changes["resize"] = res
		self.touched[device.disk.device.path] = True
		# Return to edit_partitions
		return self.edit_partitions(information=_("Changes marked succesfully. Now write the changes in memory."))
	
	
	def edit_partitions_unmark(self, device, device_changes):
		""" Unmarks changes that should be done into the partition. """
		
		self.header(_("Unmark changes"))
		
		if not device_changes:
			# No changes made!
			return self.edit_partitions(information=_("You didn't have made changes!"))
		
		if type(device) == lib.p.disk.Disk:
			# It is a Disk object, we should use Disk.device
			device = device.device
		
		num = 0
		actions = {}
		actions[0] = (_("Unmark all changes"), "all")
		for act, value in device_changes.iteritems():
			num += 1
			actions[num] = (_("Unmark '%(action)s' (value: %(value)s)") % {"action":act, "value":value}, act)
		
		# Print actions
		for num, act in actions.iteritems():
			print(" %d) %s") % (num, act[0])
		print

		result = self.entry(_("Please insert your action here"))
		try:
			result = int(result)
		except:
			return self.edit_partitions(warning=_("You didn't entered a valid action."))
		if not result in actions:
			return self.edit_partitions(warning=_("You didn't entered a valid action."))

		# We can continue with the deletion of specified action
		if actions[result][1] == "all":
			# We should delete all
			device_changes.clear()
		elif actions[result][1] == "format":
			# We should remove format and format_real
			del device_changes["format"]
			del device_changes["format_real"]
		else:
			del device_changes[actions[result][1]]
		
		# Return to main edit_partitions window.
		return self.edit_partitions(information=_("Items unmarked successfully."))
	
	def edit_partitions_write(self):
		""" Writes, in memory, the changes made. """
		
		self.header(_("Write to memory"))
		
		print(_("Do you want to write to memory your changes?"))
		print(_("This will let you continue to manage the partitioning scheme.") + "\n")
		print(_("%(note)s: This will %(not)s write the changes to the disk! It only simulates it. You should write to memory every time you delete and resize partitions. This will let you add new partitions on the freed space.") % {"note":bold(_("NOTE")), "not":bold(_("not"))})
		print(_("You can always restore original structure via the appropriate option into the main menu."))
		print
		
		res = self.question(_("Do you want to write to memory the changes?"), default=False)
		
		if res:
			failed = lib.write_memory(self.changed)	
			if failed != {}:
				return self.edit_partitions(warning=_("Something has failed: %s!") % str(failed))
			else:
				return self.edit_partitions(information=_("Ok! You can continue."))
	
	def print_devices_partitions(self, interactive=False, only_disks=False, skip_notable=False):
		""" Prints hard disks and partititons """	

		num = 0
		choices = {}

		for device, obj in self.devices.iteritems():

			disk = self.disks[device]

			# If should skip disks without table, do it now.
			if skip_notable:
				if disk == "notable":
					verbose("Disk %s has no partition table. Create a partition table then re-run this action." %  device)
					continue
	
			num +=1
			if interactive:
				_num = "%s) " % num
			else:
				_num = ""

			choices[num] = disk

			if disk == "notable": choices[num] = obj
			
			# Cache obj in self.changed
			if not obj.path in self.changed:
				self.changed[obj.path] = {"obj":choices[num], "changes":{}}
			
			# Check if this should be changed.
			if obj.path in self.changed and not self.changed[obj.path]["changes"] == {}:
				_changed = ": " + str(self.changed[obj.path]["changes"])
			else:
				_changed = ""
			print("%s%s - %s (%s GB)%s" % (_num, obj.path, obj.model, round(obj.getSize(unit="GB"), 2),_changed))
			
			if disk == "notable":
				print
				print("   No partition table.")
				print
			
			if not only_disks and disk != "notable":
				print
				# now print available partitions.
				for part in list(disk._partitions) + disk.getFreeSpacePartitions():
					if part.fileSystem == None and not part.number == -1 and not part.type == 2:
						# If filesystem == None, skip.
						_fs = _("not formatted")
					elif part.number == -1:
						_fs = _("free space")
					elif part.type == 2:
						# Extended partition
						_fs = _("extended")
					else:
						_fs = part.fileSystem.type
					
					if part.name:
						_name = part.name
					else:
						_name = "Untitled"
									
					if int(part.getSize("GB")) > 0:
						# We can use GigaBytes to represent partition size.
						_size = round(part.getSize("GB"), 2)
						_unit = "GB"
					elif int(part.getSize("MB")) > 0:
						# Partition is too small to be represented with gigabytes. Use megabytes instead.
						_size = round(part.getSize("MB"), 2)
						_unit = "MB"
					else:
						# Last try.. using kilobytes
						_size = round(part.getSize("kB"), 2)
						_unit = "kB"

					# Cache part in self.changed
					if not part.path in self.changed:
						self.changed[part.path] = {"obj":part, "changes":{}}

					__changes = copy.copy(self.changed[part.path]["changes"])
					if "format_real" in __changes:
						del __changes["format_real"]

					# Check if this should be changed.
					if part.path in self.changed and not __changes == {}:
						_changed = ": " + str(__changes)
					else:
						_changed = ""

					num +=1
					
					if interactive:
						_num = "%s) " % num
						choices[num] = part
					else:
						_num = ""

					if part.path in self.distribs:
						# This partition contains a distribution!
						_moarspace = "%s: " % bold(self.distribs[part.path])
					else:
						_moarspace = ""
					print("   %s%s%s (%s) - %s (%s %s)%s" % (_num, _moarspace, _name, part.path, _fs, _size, _unit, _changed))
			
				print
		
		if interactive:
			if not only_disks:
				# Guided partitioning
				num += 1
				choices[num] = "automatic"
				print("%s) " % num + bold(_("Automatic partitioning")))
				
				# Write to memory
				num += 1
				choices[num] = "write"
				print("%s) " % num + _("Write to memory"))
				
				# Reload original structure
				num += 1
				choices[num] = "reload"
				print("%s) " % num + _("Reload original structure"))
				
				# Commit
				num += 1
				choices[num] = "commit"
				print("%s) " % num + _("Commit"))
			
			# back
			num += 1
			choices[num] = "back"
			print("%s) " % num + _("<- Back") + "\n")
		
		if interactive:
			# Prompt
			res = self.entry(_("Enter the number of the partition(s)/device(s) you want to edit here"))
			
			return res, choices
