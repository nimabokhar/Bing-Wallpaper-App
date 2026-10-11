package com.nimabokhar.bingwallpaper

import android.content.Context

object Settings {
    private const val PREFS = "settings"
    private const val KEY_DAILY = "daily_enabled"
    private const val KEY_MARKET = "market"

    fun isDailyEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_DAILY, true)

    fun setDailyEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY_DAILY, enabled).apply()
        if (enabled) WallpaperWorker.schedule(context) else WallpaperWorker.cancel(context)
    }

    /** The market the user picked, or null to follow the device's region. */
    fun chosenMarket(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_MARKET, null)

    fun setChosenMarket(context: Context, market: String?) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_MARKET, market).apply()
    }

    fun market(context: Context): String = chosenMarket(context) ?: BingApi.deviceMarket()
}
