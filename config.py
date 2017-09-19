patchlist = "patchlist-android-170628"

rebasedb = 'rebase.db'
upstreamdb = 'upstream.db'
nextdb = 'next.db'

rebase_baseline_branch = 'android-4.9'
android_baseline_branch = "android-4.9"

rebase_baseline = 'v4.9'
stable_baseline = 'v4.9.34'
rebase_target = 'v4.12-rc7'

# chromeos_path = "linux-chrome"
stable_path = "linux-stable"
android_path = "linux-android"
upstream_path = "linux-upstream"
next_path = "linux-next"

droplist = [
	( "dirpath", "summary" )
	]

topiclist = [ [ "Documentation/android.txt" ],
	[ "drivers/staging/android/ashmem.c", "drivers/staging/android/ashmem.h" ],
	[ "drivers/staging/android/lowmemorykiller.c" ],
	[ "drivers/staging/android/fiq_debugger", "arch/arm/common/fiq_glue.S",
	  "arch/arm/common/fiq_glue_setup.c", "arch/arm/include/asm/fiq_glue.h",
	  "arch/arm/common/fiq_debugger.c", "arch/arm/common/fiq_debugger_ringbuf.h",
	  "arch/arm/include/asm/fiq_debugger.h" ],
	[ "drivers/staging/android/ion" ],
	[ "drivers/staging/android" ],
	[ "drivers/staging/goldfish", "drivers/platform/goldfish", "drivers/input/keyboard/goldfish_events.c",
	  "drivers/video/fbdev/goldfishfb.c" ],
	[ "drivers/dma-buf" ],
	[ "drivers/gpu" ],
	[ "drivers/hid" ],
	[ "drivers/input", "include/uapi/linux/keychord.h" ],
	[ "drivers/md" ],
	[ "drivers/misc" ],
	[ "drivers/mmc" ],
	[ "drivers/mtd" ],
	[ "include/linux/android_aid.h",
	  "include/linux/netfilter", "net/netfilter" ],
	[ "drivers/net", "include/linux/if_pppolac.h", "include/linux/socket.h",
	  "include/linux/wlan_plat.h" ],
	[ "net", "Documentation/networking" ],
	[ "drivers/platform" ],
	[ "drivers/usb", "include/linux/usb" ],
	[ "fs" ],
	[ "security" ],
	]
