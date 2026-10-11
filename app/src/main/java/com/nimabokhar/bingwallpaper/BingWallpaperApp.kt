package com.nimabokhar.bingwallpaper

import android.app.Application

class BingWallpaperApp : Application() {
    override fun onCreate() {
        super.onCreate()
        if (Settings.isDailyEnabled(this)) WallpaperWorker.schedule(this)
    }
}
