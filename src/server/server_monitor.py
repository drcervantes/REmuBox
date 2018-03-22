import psutil
import os
import os.path

def get_cpu_percent():
	return psutil.cpu_percent()

def get_virtual_memory():
	# Update stats using the standard system lib
	# Grab MEM using the PSUtil virtual_memory method
	vm_stats = psutil.virtual_memory()

	# Get all the memory stats (copy/paste of the PsUtil documentation)
	# total: total physical memory available.
	# available: the actual amount of available memory that can be given instantly to processes that request more memory in bytes; this is calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux) and it is supposed to be used to monitor actual memory usage in a cross platform fashion.
	# percent: the percentage usage calculated as (total - available) / total * 100.
	# used: memory used, calculated differently depending on the platform and designed for informational purposes only.
	# free: memory not being used at all (zeroed) that is readily available; note that this doesn’t reflect the actual memory available (use ‘available’ instead).
	# Platform-specific fields:
	# buffers: (Linux, BSD): cache for things like file system metadata.
	# cached: (Linux, BSD): cache for various things.
	stats = {}
	for stat in ['total', 'available', 'percent', 'used', 'free', 'buffers', 'cached']:
		if hasattr(vm_stats, stat):
			value = getattr(vm_stats, stat)
			stats[stat] = value

	# Calculate free/used memory for Linux
	stats['free'] = stats['available']
	if hasattr(stats, 'buffers'):
		stats['free'] += stats['buffers']
	if hasattr(stats, 'cached'):
		stats['free'] += stats['cached']
	stats['used'] = stats['total'] - stats['free']

	return stats

def get_disk_usage():
	drive = os.path.splitdrive(os.getcwd())[0]
	drive_stats = psutil.disk_usage(drive)

	stats = {}
	for stat in ['total', 'used', 'free', 'percent']:
		if hasattr(drive_stats, stat):
			value = getattr(drive_stats, stat)
			stats[stat] = value

	return stats

def get_server_stats():
	stats = {}
	stats["cpu"] = get_cpu_percent()
	stats["virtual-memory"] = get_virtual_memory()
	stats["disk"] = get_disk_usage()

	return stats