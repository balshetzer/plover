# Set PYTHON to the version to be deployed. This may or may not be the default
# installation.
PYTHON ?= python

all: Plover.dmg

dist/Plover.app:
	$(PYTHON) setup.py py2app
	rm ../launch.py

Plover.dmg: dist/Plover.app
	cp plover_template.dmg.gz plover_template_tmp.dmg.gz
	gunzip plover_template_tmp.dmg.gz 
	hdiutil resize -size 100m plover_template_tmp.dmg 
	mkdir plover_mountpoint
	hdiutil attach plover_template_tmp.dmg -noautoopen -quiet -mountpoint plover_mountpoint
	rm -rf plover_mountpoint/Plover.app
	ditto dist/Plover.app plover_mountpoint/Plover.app
	hdiutil detach $$(hdiutil info | grep plover_mountpoint | grep Apple_HFS | cut -f1)
	rmdir plover_mountpoint
	hdiutil convert plover_template_tmp.dmg -format UDZO -imagekey zlib-level=9 -o Plover.dmg
	rm plover_template_tmp.dmg

.PHONY: clean
clean:
	-rm -rf build/ dist/ Plover.dmg
