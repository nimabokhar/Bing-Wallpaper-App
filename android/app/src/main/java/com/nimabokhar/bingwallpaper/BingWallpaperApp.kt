package com.nimabokhar.bingwallpaper

import android.app.Application
import androidx.appcompat.app.AppCompatDelegate
import com.google.android.material.color.DynamicColors

class BingWallpaperApp : Application() {
    override fun onCreate() {
        super.onCreate()
        AppCompatDelegate.setDefaultNightMode(Settings.themeMode(this).nightMode)
        // Material You: on Android 12+ the app takes its colours from the wallpaper.
        DynamicColors.applyToActivitiesIfAvailable(this)
        ImageLoader.trimDisk(this)
        if (Settings.isDailyEnabled(this)) WallpaperWorker.schedule(this, replace = false)
    }
}
