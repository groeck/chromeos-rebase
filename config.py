# -*- coding: utf-8 -*-"

rebasedb = 'rebase419.db'
upstreamdb = 'upstream419.db'
nextdb = 'next419.db'

rebase_baseline_branch = 'chromeos-4.14'
android_baseline_branch = "android-4.14"

android_site = "https://android.googlesource.com/"
kernel_site = "https://git.kernel.org/"
chromium_site = "https://chromium.googlesource.com/"

android_repo = android_site + "kernel/common"
next_repo = kernel_site + "pub/scm/linux/kernel/git/next/linux-next"
upstream_repo = kernel_site + "pub/scm/linux/kernel/git/torvalds/linux"
stable_repo = kernel_site + "pub/scm/linux/kernel/git/stable/linux-stable"
chromeos_repo = chromium_site + "chromiumos/third_party/kernel"

rebase_baseline = 'v4.14'
stable_baseline = 'v4.14.73'
rebase_target = 'v4.19-rc7'

chromeos_path = "linux-chrome"
stable_path = "linux-stable"
android_path = "linux-android"
upstream_path = "linux-upstream"
next_path = "linux-next"

# Clear subject_droplist as follows to keep andoid patches
# subject_droplist = []
subject_droplist = ["ANDROID:", "Android:", "android:"]

droplist = [('drivers/net/wireless/iwl7000', 'Intel'),
#           ('drivers/gpu/drm/i915', 'Intel'),
#           ('drivers/gpu/drm/amd', 'AMD')
	    ]

topiclist = \
    [["chromeos", "COMMIT-QUEUE.ini", "PRESUBMIT.cfg"],
     ["drivers/extcon/extcon-cros_ec",
      "Documentation/devicetree/bindings/extcon/extcon-cros-ec.txt",
      "drivers/mfd/cros_ec", "drivers/power/cros",
      "drivers/rtc/rtc-cros-ec", "drivers/platform/chrome",
      "drivers/platform/x86/chrome", "drivers/platform/arm/chrome",
      "drivers/input/keyboard/cros_ec",
      "drivers/pwm/pwm-cros-ec.c", "drivers/iio/common/cros_ec_sensors",
      "drivers/regulator/cros_ec",
      "drivers/i2c/busses/i2c-cros-ec", "include/linux/mfd/cros_ec",
      "include/linux/chromeos",
      "Documentation/devicetree/bindings/chrome"],
     ["drivers/gpu/drm/bridge/analogix",
      "include/drm/bridge/analogix_dp.h",
      "Documentation/devicetree/bindings/display/bridge/analogix_dp.txt",
      "Documentation/devicetree/bindings/drm/bridge/anx7688.txt"],
     ["drivers/power", "drivers/base/power", "kernel/power",
      "include/dt-bindings/power", "include/linux/power",
      "include/linux/pm", "Documentation/power", "arch/x86/power",
      "Documentation/devicetree/bindings/power"],
     ["drivers/usb", "include/linux/usb", "include/uapi/linux/usb",
      "Documentation/devicetree/bindings/usb"],
     ["drivers/gpu/drm/amd"],
     ["drivers/gpu/drm/i915"],
     ["drivers/gpu", "include/drm", "Documentation/devicetree/bindings/drm",
      "include/uapi/drm"],
     ["drivers/media", "include/media", "include/uapi/linux/videodev2.h",
      "include/uapi/linux/v4l2-controls.h"],
     ["drivers/input/touchscreen/atmel_mxt_ts.c",
      "include/linux/platform_data/atmel_mxt_ts.h"],
     ["drivers/input", "include/linux/input"],
     ["drivers/iio", "drivers/staging/iio", "Documentation/driver-api/iio",
      "Documentation/devicetree/bindings/iio",
      "Documentation/devicetree/bindings/staging/iio",
      "Documentation/iio", "include/linux/iio", "include/uapi/linux/iio",
      "include/dt-bindings/iio"],
     ["drivers/mmc", "Documentation/mmc", "include/linux/mmc",
      "include/uapi/linux/mmc"],
     ["drivers/mtd", "include/linux/mtd", "include/uapi/mtd",
      "Documentation/mtd", "Documentation/devicetree/bindings/mtd"],
     ["net/bluetooth", "drivers/bluetooth",
      "Documentation/devicetree/bindings/net/btusb.txt",
      "include/net/bluetooth"],
     ["net/wireless", "drivers/net/wireless",
      "Documentation/devicetree/bindings/net/wireless"],
     ["drivers/net/usb", "net", "drivers/net", "include/linux/tcp.h",
      "include/uapi/linux/tcp.h",
      "include/net", "include/dt-bindings/net", "include/linux/net",
      "include/uapi/linux/sockios.h"],
     ["sound/soc/intel"],
     ["sound", "Documentation/devicetree/bindings/sound", "include/sound",
      "include/uapi/sound"],
     ["security", "include/linux/alt-syscall.h",
      "arch/arm64/kernel/alt-syscall.c",
      "arch/x86/kernel/alt-syscall.c", "kernel/alt-syscall.ch"],
     ["android", "Documentation/android", "drivers/android",
      "drivers/staging/android",
      "include/linux/android", "include/uapi/linux/android"],
     ["fs/pstore", "include/linux/pstore",
      "Documentation/devicetree/bindings/reserved-memory/ramoops.txt",
      "Documentation/devicetree/bindings/misc/ramoops.txt",
      "Documentation/ramoops.txt"],
     ["fs"],
     ["drivers/hid"],
     ["drivers/thermal", "include/linux/thermal",
      "Documentation/devicetree/bindings/thermal"],
     ["Documentation/devicetree/bindings/regulator", "drivers/regulator",
      "include/linux/regulator"],
     ["drivers/scsi"],
     ["drivers/firmware/google"],
     ["drivers/char/tpm", "Documentation/devicetree/bindings/security/tpm"]
    ]
