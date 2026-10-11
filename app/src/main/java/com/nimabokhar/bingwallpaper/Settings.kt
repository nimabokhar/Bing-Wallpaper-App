package com.nimabokhar.bingwallpaper

import android.content.Context

object Settings {
    private const val PREFS = "settings"
    private const val KEY_DAILY = "daily_enabled"

    fun isDailyEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_DAILY, true)

    fun setDailyEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY_DAILY, enabled).apply()
        if (enabled) WallpaperWorker.schedule(context) else WallpaperWorker.cancel(context)
    }
}
