[app]

title = StockDeskPro
package.name = stockdeskpro
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0

requirements = python3,kivy==2.2.1

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b
android.arch = arm64-v8a

android.permissions = INTERNET

android.accept_sdk_license = True
log_level = 2
