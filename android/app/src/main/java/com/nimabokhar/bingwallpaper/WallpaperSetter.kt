package com.nimabokhar.bingwallpaper

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import kotlin.math.roundToInt

/** Where to apply a wallpaper. */
enum class WallpaperTarget(val flags: Int) {
    BOTH(WallpaperManager.FLAG_SYSTEM or WallpaperManager.FLAG_LOCK),
    HOME(WallpaperManager.FLAG_SYSTEM),
    LOCK(WallpaperManager.FLAG_LOCK),
}

object WallpaperSetter {
    private const val PREFS = "wallpaper"
    // Newest Bing image the daily update has already handled. The daily update
    // only changes the wallpaper when Bing publishes something newer, so a
    // manually picked older image isn't overwritten until the next new one.
    private const val KEY_SEEN_NEWEST_ID = "last_id"
    private const val KEY_LAST_TITLE = "last_title"
    private const val KEY_LAST_TIME = "last_time"

    /**
     * Applies the newest Bing image to the home and lock screen. Returns the
     * applied image, or null if it was already handled and [force] is false.
     */
    fun applyNewest(
        context: Context,
        force: Boolean,
        image: BingImage = BingApi.fetchImageOfTheDay(Settings.market(context)),
    ): BingImage? {
        if (!force && prefs(context).getString(KEY_SEEN_NEWEST_ID, null) == image.id) return null
        apply(context, image, WallpaperTarget.BOTH)
        markNewestSeen(context, image.id)
        return image
    }

    /** Downloads [image] at full size and applies it to [target]. */
    fun apply(context: Context, image: BingImage, target: WallpaperTarget) {
        val bitmap = BingApi.downloadBitmap(image, Settings.resolution(context))
        val crop = centerCropFor(context, bitmap)
        WallpaperManager.getInstance(context).setBitmap(bitmap, crop, true, target.flags)
        bitmap.recycle()

        prefs(context).edit()
            .putString(KEY_LAST_TITLE, image.title)
            .putLong(KEY_LAST_TIME, System.currentTimeMillis())
            .apply()
    }

    fun markNewestSeen(context: Context, id: String) {
        prefs(context).edit().putString(KEY_SEEN_NEWEST_ID, id).apply()
    }

    fun lastApplied(context: Context): Pair<String, Long>? {
        val prefs = prefs(context)
        val time = prefs.getLong(KEY_LAST_TIME, 0L)
        if (time == 0L) return null
        return (prefs.getString(KEY_LAST_TITLE, null) ?: "") to time
    }

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /**
     * Crop hint that keeps the centre of the image at the shape of the widest
     * screen the device has (the inner screen on a foldable). Narrower screens
     * are centre-cropped further by the system.
     */
    private fun centerCropFor(context: Context, bitmap: Bitmap): Rect {
        val screenRatio = ScreenShapes.widestRatio(context).takeIf { it > 0f } ?: (9f / 16f)
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
