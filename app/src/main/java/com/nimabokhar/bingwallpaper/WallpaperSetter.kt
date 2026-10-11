package com.nimabokhar.bingwallpaper

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import kotlin.math.roundToInt

object WallpaperSetter {
    private const val PREFS = "wallpaper"
    private const val KEY_LAST_ID = "last_id"
    private const val KEY_LAST_TITLE = "last_title"
    private const val KEY_LAST_TIME = "last_time"

    /**
     * Downloads today's Bing image and applies it to the home and lock screen.
     * Returns the applied image, or null if it was already applied and [force] is false.
     */
    fun applyToday(context: Context, force: Boolean): BingImage? {
        val image = BingApi.fetchImageOfTheDay(Settings.market(context))
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!force && prefs.getString(KEY_LAST_ID, null) == image.id) return null

        val bitmap = BingApi.downloadBitmap(image)
        val manager = WallpaperManager.getInstance(context)
        val crop = centerCropFor(context, bitmap)
        manager.setBitmap(bitmap, crop, true, WallpaperManager.FLAG_SYSTEM or WallpaperManager.FLAG_LOCK)
        bitmap.recycle()

        prefs.edit()
            .putString(KEY_LAST_ID, image.id)
            .putString(KEY_LAST_TITLE, image.title)
            .putLong(KEY_LAST_TIME, System.currentTimeMillis())
            .apply()
        return image
    }

    fun lastApplied(context: Context): Pair<String, Long>? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val time = prefs.getLong(KEY_LAST_TIME, 0L)
        if (time == 0L) return null
        return (prefs.getString(KEY_LAST_TITLE, null) ?: "") to time
    }

    /** Crop hint that keeps the centre of the image at the screen's aspect ratio. */
    private fun centerCropFor(context: Context, bitmap: Bitmap): Rect {
        val metrics = context.resources.displayMetrics
        val screenW = minOf(metrics.widthPixels, metrics.heightPixels).toFloat()
        val screenH = maxOf(metrics.widthPixels, metrics.heightPixels).toFloat()
        val screenRatio = screenW / screenH
        val imageRatio = bitmap.width.toFloat() / bitmap.height

        return if (imageRatio > screenRatio) {
            val w = (bitmap.height * screenRatio).roundToInt()
            val left = (bitmap.width - w) / 2
            Rect(left, 0, left + w, bitmap.height)
        } else {
            val h = (bitmap.width / screenRatio).roundToInt()
            val top = (bitmap.height - h) / 2
            Rect(0, top, bitmap.width, top + h)
        }
    }
}
