patchlist = "patchlist-170626"

rebasedb = 'rebase412.db'
upstreamdb = 'upstream412.db'
nextdb = 'next412.db'

rebase_baseline_branch = 'chromeos-4.4'
android_baseline_branch = "android-4.4"

rebase_baseline = 'v4.4'
stable_baseline = 'v4.4.70'
rebase_target = 'v4.12'

chromeos_path = "linux-chrome"
stable_path = "linux-stable"
android_path = "linux-android"
upstream_path = "linux-upstream"
next_path = "linux-next"

droplist = [ ("drivers/net/wireless/iwl7000", "intel"),
	( "include/config/iwl7000", "intel" ),
	( "drivers/gpu/drm/i915", "intel" ),
	( "drivers/gpu/drm/mediatek", "mediatek" ),
	( "drivers/thermal/mtk_thermal", "mediatek" ),
	( "drivers/clk/mediatek", "mediatek" ),
	( "drivers/soc/mediatek", "mediatek" ),
	( "drivers/media/platform/mtk", "mediatek" ),
	( "Documentation/devicetree/bindings/media/mediatek", "mediatek" ),
	( "Documentation/devicetree/bindings/soc/mediatek", "mediatek" ),
	( "sound/soc/mediatek", "mediatek" ),
	( "drivers/cpufreq/mt8173", "mediatek" ),
	( "arch/arm64/boot/dts/mediatek", "mediatek" ),
	( "drivers/net/wireless/ar10k", "atheros" ),
	( "drivers/gpu/drm/img-rogue", "imgtec" )
	]

topiclist = [ [ "chromeos", "COMMIT-QUEUE.ini", "PRESUBMIT.cfg"],
	[ "drivers/extcon/extcon-cros_ec", "Documentation/devicetree/bindings/extcon/extcon-cros-ec.txt",
	  "drivers/mfd/cros_ec", "drivers/power/cros", "drivers/rtc/rtc-cros-ec", "drivers/platform/chrome",
	  "drivers/platform/x86/chrome", "drivers/platform/arm/chrome", "drivers/input/keyboard/cros_ec",
	  "drivers/pwm/pwm-cros-ec.c", "drivers/iio/common/cros_ec_sensors", "drivers/regulator/cros_ec",
	  "drivers/i2c/busses/i2c-cros-ec", "include/linux/mfd/cros_ec", "include/linux/chromeos",
	  "Documentation/devicetree/bindings/chrome" ],
	[ "drivers/gpu/drm/bridge/analogix", "include/drm/bridge/analogix_dp.h",
	  "Documentation/devicetree/bindings/display/bridge/analogix_dp.txt",
	  "Documentation/devicetree/bindings/drm/bridge/anx7688.txt" ],
	[ "drivers/gpu/arm/midgard", "Documentation/devicetree/bindings/arm/mali-midgard.txt" ],
	[ "arch/arm64/boot/dts/rockchip", "arch/arm/boot/dts/rockchip", "arch/arm/boot/dts/rk3" ],
	[ "drivers/devfreq/rk3399", "drivers/devfreq/event/rockchip" ],
	[ "drivers/clk/rockchip", "include/dt-bindings/clock/rk3399" ],
	[ "drivers/spi/spi-rockchip" ],
	[ "drivers/phy/phy-rockchip", "Documentation/devicetree/bindings/phy/phy-rockchip" ],
	[ "drivers/usb/dwc3/dwc3-rockchip" ],
	[ "drivers/crypto/rockchip" ],
	[ "drivers/gpu/drm/rockchip",
	  "Documentation/devicetree/bindings/display/rockchip",
	  "drivers/media/platform/rockchip-vpu",
	  "drivers/media/platform/rk3288",
	  "Documentation/devicetree/bindings/display/rockchip/analogix_dp-rockchip.txt" ],
	[ "include/soc/rockchip", "sound/soc/rockchip", "drivers/soc/rockchip",
	  "Documentation/devicetree/bindings/sound/rockchip", "arch/arm/mach-rockchip" ],
	[ "include/dt-bindings/power/rk3399" ],
	[ "Documentation/devicetree/bindings/pci/rockchip", "drivers/pci/host/pcie-rockchip" ],
	[ "drivers/thermal/rockchip" ],
	[ "drivers/iommu/rockchip" ],
	[ "drivers/power", "drivers/base/power", "kernel/power", "include/dt-bindings/power",
	  "include/linux/power", "include/linux/pm", "Documentation/power", "arch/x86/power",
	  "Documentation/devicetree/bindings/power" ],
	[ "drivers/usb", "include/linux/usb", "include/uapi/linux/usb",
	  "Documentation/devicetree/bindings/usb" ],
	[ "drivers/gpu", "include/drm", "Documentation/devicetree/bindings/drm", "include/uapi/drm" ],
	[ "drivers/media", "include/media", "include/uapi/linux/videodev2.h",
	  "include/uapi/linux/v4l2-controls.h" ],
	[ "drivers/input/touchscreen/atmel_mxt_ts.c", "include/linux/platform_data/atmel_mxt_ts.h" ],
	[ "drivers/input", "include/linux/input" ],
	[ "drivers/iio", "drivers/staging/iio", "Documentation/driver-api/iio",
	  "Documentation/devicetree/bindings/iio", "Documentation/devicetree/bindings/staging/iio",
	  "Documentation/iio", "include/linux/iio", "include/uapi/linux/iio", "include/dt-bindings/iio" ],
	[ "drivers/mmc", "Documentation/mmc", "include/linux/mmc", "include/uapi/linux/mmc" ],
	[ "drivers/mtd", "include/linux/mtd", "include/uapi/mtd", "Documentation/mtd",
	  "Documentation/devicetree/bindings/mtd" ],
	[ "net/bluetooth", "drivers/bluetooth", "Documentation/devicetree/bindings/net/btusb.txt",
	  "include/net/bluetooth" ],
	[ "net/wireless", "drivers/net/wireless", "Documentation/devicetree/bindings/net/wireless" ],
	[ "drivers/net/usb", "net", "drivers/net", "include/linux/tcp.h", "include/uapi/linux/tcp.h",
	  "include/net", "include/dt-bindings/net", "include/linux/net", "include/uapi/linux/sockios.h" ],
	[ "sound/soc/intel" ],
	[ "sound", "Documentation/devicetree/bindings/sound", "include/sound", "include/uapi/sound" ],
	[ "security", "include/linux/alt-syscall.h", "arch/arm64/kernel/alt-syscall.c",
	  "arch/x86/kernel/alt-syscall.c", "kernel/alt-syscall.ch" ],
	[ "android", "Documentation/android", "drivers/android", "drivers/staging/android",
	  "include/linux/android", "include/uapi/linux/android" ],
	[ "fs/pstore", "include/linux/pstore",
	  "Documentation/devicetree/bindings/reserved-memory/ramoops.txt",
	  "Documentation/devicetree/bindings/misc/ramoops.txt", "Documentation/ramoops.txt" ],
	[ "fs" ],
	[ "drivers/hid" ],
	[ "drivers/thermal", "include/linux/thermal", "Documentation/devicetree/bindings/thermal" ],
	[ "Documentation/devicetree/bindings/regulator", "drivers/regulator", "include/linux/regulator" ],
	[ "drivers/scsi" ],
	[ "drivers/firmware/google" ],
	[ "drivers/char/tpm", "Documentation/devicetree/bindings/security/tpm" ]
	]
