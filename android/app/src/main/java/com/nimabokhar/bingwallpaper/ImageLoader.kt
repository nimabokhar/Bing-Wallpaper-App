package com.nimabokhar.bingwallpaper

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import android.util.LruCache
import androidx.annotation.MainThread
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import kotlin.math.roundToInt

/**
 * Loads images for the screen without ever blocking the main thread.
 *
 * Downloads are kept on disk, so reopening the app or scrolling back shows
 * images straight away. Each image is decoded at the size it is shown at (never
 * the full source size) on a background thread, and kept in memory as a
 * hardware bitmap where available, so drawing it costs the UI thread nothing.
 * Requests for the same image share one download and one decode, and keep going
 * if the view that asked scrolls away, so the work is not wasted.
 *
 * Call everything from the main thread.
 */
@OptIn(ExperimentalCoroutinesApi::class)
object ImageLoader {
    private val memory = object : LruCache<String, Bitmap>(cacheSizeKb()) {
        // Hardware bitmaps report their size inconsistently; count 4 bytes a pixel.
        override fun sizeOf(key: String, value: Bitmap) = value.width * value.height * 4 / 1024
    }
    private val decodes = HashMap<String, Deferred<Bitmap?>>()
    private val downloads = HashMap<String, Deferred<File?>>()
    // Plain Main (not immediate): a task never starts before it is registered above.
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    // A few parallel downloads and decodes keep the network and CPU busy without
    // starving the threads that draw the screen.
    private val network = Dispatchers.IO.limitedParallelism(4)
    private val decoder = Dispatchers.Default.limitedParallelism(2)

    private val maxDiskAge = TimeUnit.DAYS.toMillis(30)

    /**
     * Returns the image already decoded for a [width] x [height] view, or null.
     * [urls] are tried in order; the first one names the image.
     */
    @MainThread
    fun cached(urls: List<String>, width: Int, height: Int): Bitmap? = memory.get(key(urls, width, height))

    /** Loads the image to fill a [width] x [height] view (center-cropped), or null if it can't be fetched. */
    @MainThread
    suspend fun load(context: Context, urls: List<String>, width: Int, height: Int): Bitmap? {
        val key = key(urls, width, height)
        memory.get(key)?.let { return it }
        val app = context.applicationContext
        val task = decodes.getOrPut(key) {
            scope.async {
                try {
                    val file = download(app, urls) ?: return@async null
                    withContext(decoder) { decode(file, width, height) }?.also { memory.put(key, it) }
                } catch (e: Exception) {
                    null
                } finally {
                    decodes.remove(key)
                }
            }
        }
        return task.await()
    }

    /** Downloads images to disk ahead of time so they appear instantly when scrolled to. */
    @MainThread
    fun prefetch(context: Context, urlLists: List<List<String>>) {
        val app = context.applicationContext
        for (urls in urlLists) scope.launch { download(app, urls) }
    }

    /** Deletes downloads that haven't been used for a month. */
    fun trimDisk(context: Context) {
        val app = context.applicationContext
        scope.launch(Dispatchers.IO) {
            val cutoff = System.currentTimeMillis() - maxDiskAge
            dir(app).listFiles()?.filter { it.lastModified() < cutoff }?.forEach { it.delete() }
        }
    }

    private suspend fun download(app: Context, urls: List<String>): File? {
        val key = urls.first()
        val task = downloads.getOrPut(key) {
            scope.async {
                try {
                    withContext(network) { fetchToDisk(app, urls) }
                } catch (e: Exception) {
                    null
                } finally {
                    downloads.remove(key)
                }
            }
        }
        return task.await()
    }

    private fun fetchToDisk(app: Context, urls: List<String>): File? {
        val dir = dir(app)
        val file = File(dir, sha1(urls.first()))
        if (file.length() > 0) {
            file.setLastModified(System.currentTimeMillis())
            return file
        }
        for (url in urls) {
            val bytes = runCatching { BingApi.httpGet(url) }.getOrNull() ?: continue
            // Write then rename, so a half-written file is never read as an image.
            val partial = File(dir, file.name + ".part")
            partial.writeBytes(bytes)
            if (partial.renameTo(file)) return file
        }
        return null
    }

    private fun decode(file: File, width: Int, height: Int): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.path, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            file.delete()
            return null
        }
        // Just big enough to cover the view, never scaled up.
        val scale = maxOf(width.toFloat() / bounds.outWidth, height.toFloat() / bounds.outHeight).coerceAtMost(1f)
        val targetWidth = (bounds.outWidth * scale).roundToInt().coerceAtLeast(1)
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= targetWidth) sample *= 2
        val options = BitmapFactory.Options().apply {
            inSampleSize = sample
            // Finish the scaling in the same decode pass.
            if (bounds.outWidth / sample > targetWidth) {
                inScaled = true
                inDensity = bounds.outWidth
                inTargetDensity = targetWidth * sample
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) inPreferredConfig = Bitmap.Config.HARDWARE
        }
        return BitmapFactory.decodeFile(file.path, options)?.also { it.prepareToDraw() }
    }

    private fun dir(app: Context) = File(app.cacheDir, "images").apply { mkdirs() }

    private fun key(urls: List<String>, width: Int, height: Int) = "${urls.first()}@${width}x$height"

    private fun sha1(text: String): String =
        MessageDigest.getInstance("SHA-1").digest(text.toByteArray()).joinToString("") { "%02x".format(it) }

    /** An eighth of the app's memory for decoded images. */
    private fun cacheSizeKb() = (Runtime.getRuntime().maxMemory() / 1024 / 8).toInt()
}
