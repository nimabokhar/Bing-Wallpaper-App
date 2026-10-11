package com.nimabokhar.bingwallpaper

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

data class BingImage(
    /** Stable id of the image, e.g. "OHR.SomePlace_EN-US1234567890". */
    val id: String,
    val title: String,
    val copyright: String,
    /** Portrait image sized for phones. */
    val portraitUrl: String,
    /** Landscape image Bing shows on its home page, used if portrait fails. */
    val fallbackUrl: String,
)

object BingApi {
    private const val BASE = "https://www.bing.com"
    private const val DEFAULT_MARKET = "en-US"

    // Markets Bing publishes a distinct image of the day for.
    private val SUPPORTED_MARKETS = setOf(
        "en-US", "en-GB", "en-AU", "en-CA", "en-IN", "en-NZ",
        "de-DE", "fr-FR", "fr-CA", "es-ES", "it-IT", "pt-BR", "ja-JP", "zh-CN",
    )

    fun marketFor(locale: Locale = Locale.getDefault()): String {
        val tag = "${locale.language}-${locale.country}"
        return SUPPORTED_MARKETS.firstOrNull { it.equals(tag, ignoreCase = true) } ?: DEFAULT_MARKET
    }

    fun fetchImageOfTheDay(market: String = marketFor()): BingImage {
        val json = JSONObject(httpGet("$BASE/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=$market").decodeToString())
        val image = json.getJSONArray("images").getJSONObject(0)
        val urlBase = image.getString("urlbase")
        return BingImage(
            id = urlBase.substringAfter("id=", urlBase),
            title = image.optString("title"),
            copyright = image.optString("copyright"),
            portraitUrl = "$BASE${urlBase}_1080x1920.jpg",
            fallbackUrl = BASE + image.getString("url"),
        )
    }

    fun downloadBitmap(image: BingImage): Bitmap {
        for (url in listOf(image.portraitUrl, image.fallbackUrl)) {
            val bytes = runCatching { httpGet(url) }.getOrNull() ?: continue
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.let { return it }
        }
        throw IOException("Could not download image ${image.id}")
    }

    private fun httpGet(url: String): ByteArray {
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 15_000
            conn.readTimeout = 30_000
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android) BingWallpaper")
            if (conn.responseCode !in 200..299) {
                throw IOException("HTTP ${conn.responseCode} for $url")
            }
            return conn.inputStream.use { it.readBytes() }
        } finally {
            conn.disconnect()
        }
    }
}
