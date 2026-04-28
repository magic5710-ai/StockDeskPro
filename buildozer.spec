[app]

title = StockDeskPro
package.name = stockdeskpro
package.domain = org.stockdeskpro

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0

requirements = python3,kivy,requests

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.add_assets = *.ttf

android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
