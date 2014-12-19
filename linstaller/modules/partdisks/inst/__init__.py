# -*- coding: utf-8 -*-
# linstaller partdisks module install - (C) 2011 Eugenio "g7" Paolantonio and the Semplice Team.
# All rights reserved. Work released under the GNU GPL license, version 3 or later.
#
# This is a module of linstaller, should not be executed as a standalone application.

import linstaller.core.module as module

from linstaller.core.main import warn,info,verbose
import linstaller.core.libmodules.partdisks.library as lib

import os

class Module(module.Module):
	def _associate_(self):
		""" Shut up associate as we do not have any frontend. """
		
		pass
		
	def start(self):
		""" Start override to unsquash. """
				
		if "partdisks" in self.modules_settings:
			settings = self.modules_settings["partdisks"]
		else:
			settings = self.settings
		
		# Mount root partition.
		root = settings["root"]

		# Ensure that is unmounted
		if os.path.ismount(self.main_settings["target"]):
			# Target mounted. Unmount
			lib.umount(path=self.main_settings["target"])
		if lib.is_mounted(root):
			# Partition mounted. Unmount
			lib.umount(path=root)
				
		# Then mount at TARGET
		lib.mount_partition(path=root, target=self.main_settings["target"])

		used = []
				
		# Mount every partition which has "useas" on it
		# Get changed.
		try:
			changed = self.modules_settings["partdisks"]["changed"]
		except:
			# Pass
			changed = {}
		
		mountpo = []
		changeslist = {}
				
		# Regenerate changed to sort it sanely
		for key, value in changed.items():
			if not "useas" in value["changes"]:
				# There isn't "useas" in changes; skipping this item
				continue

			mountpo.append(value["changes"]["useas"])
			changeslist[value["changes"]["useas"]] = key
		
		mountpo.sort()
				
		for point in mountpo:
						
			# Get correct partition
			key = changeslist[point]
			# Get value
			value = changed[key]
									
			# Get useas
			useas = value["changes"]["useas"]
			
			if useas in ("/","swap"):
				# Root or swap, do not use it
				continue
						
			# Mount key to mountpoint
			if lib.is_mounted(key):
				# Umount
				lib.umount(path=key)
			if useas == "/boot/efi":
				# If this is going to be the /boot/efi partition
				# we should make sure that it's going to have the
				# proper partition type set to EFI System Partition
				lib.prepareforEFI(lib.return_partition(key))
							
			# If we mount_on_install, simply set drop to False, as we should use it anyway
			if ("mount_on_install" in value["changes"] and value["changes"]["mount_on_install"]) or useas in ("/boot","/boot/efi"):
				# Create mountpoint
				mountpoint = self.main_settings["target"] + useas # useas begins with a /, so os.path.join doesn't work
				if not os.path.exists(mountpoint): os.makedirs(mountpoint)

				lib.mount_partition(path=key, target=mountpoint)
				# Partition will be used during unsquash, we should remember when linstaller will execute revert
				used.append(key)
				
		# Store used
		self.settings["used"] = used
			

	def revert(self):
		""" Umounts TARGET. """
		
		# Ensure that is mounted
		if not os.path.ismount(self.main_settings["target"]):
			# Umounted. pass.
			return
		
		# See if "used" was... used :)
		if "partdisks.inst" in self.modules_settings and "used" in self.modules_settings["partdisks.inst"]:
			_used = self.modules_settings["partdisks.inst"]["used"]
			_used.reverse()
			if _used:
				for part in _used:
					if lib.is_mounted(part):
						try:
							lib.umount(path=part, tries=5)
						except:
							pass
		
		# Umount target, finally.
		try:
			lib.umount(path=self.main_settings["target"], tries=5)
		except:
			pass
	
	def seedpre(self):
		""" Cache settings """
		
		self.cache("used")
