[app]

title = StockDeskPro
package.name = stockdeskpro
package.domain = org.stockdeskpro

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json

version = 1.0

requirements = python3,kivy==2.2.1,requests

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.accept_sdk_license = True

android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.archs = arm64-v8a

android.add_assets = NotoSansTC-VariableFont_wght.ttf

log_level = 2

[buildozer]

log_level = 2
warn_on_root = 1
