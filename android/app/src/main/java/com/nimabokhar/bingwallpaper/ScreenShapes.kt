package com.nimabokhar.bingwallpaper

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.view.WindowManager

/**
 * Remembers the shapes of the screens this device has shown the app on, so one
 * wallpaper can be cropped to look right on every one of them. On a foldable the
 * cover screen is tall and narrow while the inner screen is close to square; the
 * wallpaper is cropped for the widest screen and the system centre-crops it
 * further for narrower ones, so it never gets zoomed in.
 */
object ScreenShapes {
    private const val PREFS = "screens"
    private const val KEY_WIDEST = "widest_ratio"

    /** Roughly the shape of a foldable's inner screen (short side / long side). */
    private const val ASSUMED_INNER_RATIO = 0.85f

    /** Records the shape of the screen the app is currently on. */
    fun recordCurrent(context: Context) {
        val ratio = currentRatio(context)
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (ratio > prefs.getFloat(KEY_WIDEST, 0f)) prefs.edit().putFloat(KEY_WIDEST, ratio).apply()
    }

    /** Short side / long side of the widest screen the wallpaper must fill. */
    fun widestRatio(context: Context): Float {
        var widest = maxOf(
            currentRatio(context),
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getFloat(KEY_WIDEST, 0f),
        )
        // Until the app has been opened unfolded, assume a foldable's inner screen.
        if (isFoldable(context)) widest = maxOf(widest, ASSUMED_INNER_RATIO)
        return widest
    }

    fun isFoldable(context: Context): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.R &&
            context.packageManager.hasSystemFeature(PackageManager.FEATURE_SENSOR_HINGE_ANGLE)

    private fun currentRatio(context: Context): Float {
        // Window metrics are only reliable from an activity; the background worker
        // falls back to display metrics, which still reflect the current screen.
        val bounds = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            runCatching { context.getSystemService(WindowManager::class.java).maximumWindowMetrics.bounds }.getOrNull()
        } else {
            null
        }
        val metrics = context.resources.displayMetrics
        val w = bounds?.width() ?: metrics.widthPixels
        val h = bounds?.height() ?: metrics.heightPixels
        if (w <= 0 || h <= 0) return 0f
        return minOf(w, h).toFloat() / maxOf(w, h)
    }
}
