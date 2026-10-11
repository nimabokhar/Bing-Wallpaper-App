package com.nimabokhar.bingwallpaper

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import org.json.JSONArray
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
    /** Full-resolution 3840x2160 image, so it can be cropped for any screen shape. */
    val uhdUrl: String,
    /** Portrait image sized for phones, used if UHD fails. */
    val portraitUrl: String,
    /** Landscape image Bing shows on its home page, used if portrait fails. */
    val fallbackUrl: String,
    /** Small portrait version for the gallery. */
    val thumbnailUrl: String,
)

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
                uhdUrl = "$BASE${urlBase}_UHD.jpg",
                portraitUrl = "$BASE${urlBase}_1080x1920.jpg",
                fallbackUrl = BASE + image.getString("url"),
                thumbnailUrl = "$BASE${urlBase}_480x800.jpg",
            )
        }
    }

    // Older images come from the community-run Bing Wallpaper Archive
    // (github.com/npanuhin/Bing-Wallpaper-Archive), which keeps every image of the
    // day per market. Australia and New Zealand aren't archived separately, so they
    // use its "rest of the world" feed.
    private const val ARCHIVE_BASE = "https://bing.npanuhin.me"
    private val ARCHIVE_MARKETS = mapOf(
        "en-US" to "US-en", "en-GB" to "GB-en", "en-CA" to "CA-en", "fr-CA" to "CA-fr",
        "en-IN" to "IN-en", "de-DE" to "DE-de", "fr-FR" to "FR-fr", "es-ES" to "ES-es",
        "it-IT" to "IT-it", "pt-BR" to "BR-pt", "ja-JP" to "JP-ja", "zh-CN" to "CN-zh",
    )
    private const val ARCHIVE_FALLBACK = "ROW-en"
    private val BING_SIZE_SUFFIX = Regex("_(UHD|\\d+x\\d+)\\.jpg")

    /**
     * The archived images for one month, newest first. Returns null when the
     * archive has no file for that month (before it starts, or not published yet).
     */
    fun fetchArchiveMonth(market: String, year: Int, month: Int): List<BingImage>? {
        val code = ARCHIVE_MARKETS[market] ?: ARCHIVE_FALLBACK
        val url = "$ARCHIVE_BASE/$code.$year.${"%02d".format(Locale.US, month)}.json"
        val body = try {
            httpGet(url).decodeToString().trim()
        } catch (e: HttpStatusException) {
            if (e.code == 404) return null else throw e
        }
        val entries = if (body.startsWith("[")) JSONArray(body) else firstArray(JSONObject(body)) ?: JSONArray()
        return (0 until entries.length()).mapNotNull { i ->
            val entry = entries.optJSONObject(i) ?: return@mapNotNull null
            val date = entry.optString("date").takeIf { it.length == 10 } ?: return@mapNotNull null
            val archiveUrl = entry.optString("url").takeIf { it.startsWith("http") } ?: return@mapNotNull null
            val bingUrl = entry.optString("bing_url").takeIf { it.startsWith("http") && BING_SIZE_SUFFIX.containsMatchIn(it) }
            BingImage(
                id = "archive-$code-$date",
                title = entry.optString("title").takeUnless { entry.isNull("title") }.orEmpty(),
                copyright = entry.optString("copyright").takeUnless { entry.isNull("copyright") }.orEmpty(),
                startDate = date.replace("-", ""),
                uhdUrl = archiveUrl,
                portraitUrl = bingUrl?.let { BING_SIZE_SUFFIX.replace(it, "_1080x1920.jpg") } ?: archiveUrl,
                fallbackUrl = archiveUrl,
                thumbnailUrl = bingUrl?.let { BING_SIZE_SUFFIX.replace(it, "_480x800.jpg") } ?: archiveUrl,
            )
        }.sortedByDescending { it.startDate }
    }

    private fun firstArray(json: JSONObject): JSONArray? =
        json.keys().asSequence().mapNotNull { json.optJSONArray(it) }.firstOrNull()

    /** Downloads the gallery thumbnail, scaled down if the source is full size. */
    fun downloadThumbnail(image: BingImage): Bitmap? = runCatching {
        val bytes = runCatching { httpGet(image.thumbnailUrl) }.getOrNull()
            ?: httpGet(image.fallbackUrl)
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= THUMBNAIL_WIDTH && bounds.outHeight / (sample * 2) >= THUMBNAIL_WIDTH) {
            sample *= 2
        }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inSampleSize = sample })
    }.getOrNull()

    private const val THUMBNAIL_WIDTH = 480

    fun downloadBitmap(image: BingImage): Bitmap {
        for (url in listOf(image.uhdUrl, image.portraitUrl, image.fallbackUrl)) {
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
                throw HttpStatusException(conn.responseCode, url)
            }
            return conn.inputStream.use { it.readBytes() }
        } finally {
            conn.disconnect()
        }
    }
}

class HttpStatusException(val code: Int, url: String) : IOException("HTTP $code for $url")
