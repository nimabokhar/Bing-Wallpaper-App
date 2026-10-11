package com.nimabokhar.bingwallpaper

import android.content.Context

/** App theme choice, in the order shown in the picker. */
enum class ThemeMode { SYSTEM, LIGHT, DARK }

object Settings {
    private const val PREFS = "settings"
    private const val KEY_DAILY = "daily_enabled"
    private const val KEY_MARKET = "market"
    private const val KEY_THEME = "theme"
    private const val KEY_RESOLUTION = "resolution"
    private const val KEY_HOUR = "schedule_hour"
    private const val KEY_MINUTE = "schedule_minute"

    // Bing publishes each market's new image around local midnight, so early
    // morning is a safe default.
    private const val DEFAULT_HOUR = 7
    private const val DEFAULT_MINUTE = 0

    fun isDailyEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_DAILY, true)

    fun setDailyEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY_DAILY, enabled).apply()
        if (enabled) WallpaperWorker.schedule(context, replace = true) else WallpaperWorker.cancel(context)
    }

    /** Time of day for the automatic change, as (hour 0-23, minute). */
    fun scheduleTime(context: Context): Pair<Int, Int> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getInt(KEY_HOUR, DEFAULT_HOUR) to prefs.getInt(KEY_MINUTE, DEFAULT_MINUTE)
    }

    fun setScheduleTime(context: Context, hour: Int, minute: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putInt(KEY_HOUR, hour)
            .putInt(KEY_MINUTE, minute)
            .apply()
        if (isDailyEnabled(context)) WallpaperWorker.schedule(context, replace = true)
    }

    /** The market the user picked, or null to follow the device's region. */
    fun chosenMarket(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_MARKET, null)

    fun setChosenMarket(context: Context, market: String?) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_MARKET, market).apply()
    }

    fun market(context: Context): String = chosenMarket(context) ?: BingApi.deviceMarket()

    fun themeMode(context: Context): ThemeMode {
        val name = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_THEME, null)
        return ThemeMode.entries.firstOrNull { it.name == name } ?: ThemeMode.SYSTEM
    }

    fun setThemeMode(context: Context, mode: ThemeMode) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_THEME, mode.name).apply()
    }

    fun resolution(context: Context): ImageResolution {
        val name = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_RESOLUTION, null)
        return ImageResolution.entries.firstOrNull { it.name == name } ?: ImageResolution.UHD
    }

    fun setResolution(context: Context, resolution: ImageResolution) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_RESOLUTION, resolution.name).apply()
    }
}
