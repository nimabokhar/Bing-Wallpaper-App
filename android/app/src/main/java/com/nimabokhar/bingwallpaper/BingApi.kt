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
    /** Day the image was Bing's image of the day, as yyyyMMdd. */
    val startDate: String,
    /** Bing image URL without the size suffix; see [ImageResolution]. */
    val urlBase: String,
    /** Landscape image Bing shows on its home page, used if the chosen size fails. */
    val fallbackUrl: String,
    /** Landscape preview for the gallery cards; see [ImageLoader]. */
    val thumbnailUrl: String,
)

/** Image sizes Bing publishes for each image of the day. */
enum class ImageResolution(val suffix: String) {
    UHD("_UHD.jpg"),
    FULL_HD("_1920x1080.jpg"),
    HD("_1366x768.jpg"),
    PORTRAIT("_1080x1920.jpg"),
}

object BingApi {
    private const val BASE = "https://www.bing.com"
    private const val DEFAULT_MARKET = "en-US"

    /** Markets Bing publishes an image of the day for, with display names. */
    val MARKETS: List<Pair<String, String>> = listOf(
        "en-US" to "United States",
        "en-GB" to "United Kingdom",
        "en-CA" to "Canada (English)",
        "fr-CA" to "Canada (French)",
        "en-AU" to "Australia",
        "en-NZ" to "New Zealand",
        "en-IN" to "India",
        "de-DE" to "Germany",
        "fr-FR" to "France",
        "es-ES" to "Spain",
        "it-IT" to "Italy",
        "pt-BR" to "Brazil",
        "ja-JP" to "Japan",
        "zh-CN" to "China",
    )

    /** The market matching the device's language and region, or en-US. */
    fun deviceMarket(locale: Locale = Locale.getDefault()): String {
        val tag = "${locale.language}-${locale.country}"
        return MARKETS.firstOrNull { it.first.equals(tag, ignoreCase = true) }?.first ?: DEFAULT_MARKET
    }

    /** Bing returns at most this many images per request. */
    const val MAX_IMAGES = 8

    /** Highest start offset Bing's feed accepts; with [MAX_IMAGES] it reaches back about 15 days. */
    const val MAX_OFFSET = 7

    fun fetchImageOfTheDay(market: String): BingImage = fetchLatest(market, 1).first()

    /** Images from Bing's own feed, newest first, starting [offset] days back. */
    fun fetchLatest(market: String, count: Int = MAX_IMAGES, offset: Int = 0): List<BingImage> {
        val json = JSONObject(httpGet("$BASE/HPImageArchive.aspx?format=js&idx=$offset&n=$count&mkt=$market").decodeToString())
        val images = json.getJSONArray("images")
        return (0 until images.length()).map { i ->
            val image = images.getJSONObject(i)
            val urlBase = image.getString("urlbase")
            BingImage(
                id = urlBase.substringAfter("id=", urlBase),
                title = image.optString("title"),
                copyright = image.optString("copyright"),
                startDate = image.optString("startdate"),
                urlBase = BASE + urlBase,
                fallbackUrl = BASE + image.getString("url"),
                thumbnailUrl = "$BASE${urlBase}_1366x768.jpg",
            )
        }
    }

    /** Downloads [image] at [resolution], falling back to other sizes if Bing doesn't have it. */
    fun downloadBitmap(image: BingImage, resolution: ImageResolution): Bitmap {
        val sizes = listOf(resolution, ImageResolution.UHD, ImageResolution.PORTRAIT).distinct()
        for (url in sizes.map { image.urlBase + it.suffix } + image.fallbackUrl) {
            val bytes = runCatching { httpGet(url) }.getOrNull() ?: continue
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.let { return it }
        }
        throw IOException("Could not download image ${image.id}")
    }

    fun httpGet(url: String): ByteArray {
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 15_000
            conn.readTimeout = 30_000
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android) BingWallpaper")
            if (conn.responseCode !in 200..299) {
                throw HttpStatusException(conn.responseCode, url)
            }
            return conn.inputStream.use { it.readBytes() }
        } finally {
            conn.disconnect()
        }
    }
}

class HttpStatusException(val code: Int, url: String) : IOException("HTTP $code for $url")
