package com.nimabokhar.bingwallpaper

import java.util.Calendar

/**
 * Pages backwards through Bing's images of the day for one market: first
 * Bing's own feed (about the last 15 days), then the archive one month at a
 * time. Not thread-safe; call [nextPage] from one coroutine at a time.
 */
class GalleryPager(private val market: String) {
    private val bingOffsets = mutableListOf(0, BingApi.MAX_OFFSET)
    private var archiveMonth: Calendar? = null
    private val seenDates = mutableSetOf<String>()
    private var oldestDate: String? = null

    var exhausted = false
        private set

    /** The next, older batch of images, newest first. Blocks on the network. */
    fun nextPage(): List<BingImage> {
        while (!exhausted) {
            val page = fetchRaw()
            val fresh = page.filter { image ->
                val older = oldestDate?.let { image.startDate < it } ?: true
                older && seenDates.add(image.startDate)
            }
            fresh.lastOrNull()?.let { oldestDate = it.startDate }
            if (fresh.isNotEmpty()) return fresh
        }
        return emptyList()
    }

    private fun fetchRaw(): List<BingImage> {
        if (bingOffsets.isNotEmpty()) {
            val offset = bingOffsets.removeAt(0)
            return try {
                BingApi.fetchLatest(market, BingApi.MAX_IMAGES, offset)
            } catch (e: Exception) {
                // The first page must come from Bing; later ones can fall through to the archive.
                if (offset == 0) throw e else emptyList()
            }
        }

        val month = archiveMonth ?: startingArchiveMonth().also { archiveMonth = it }
        val images = BingApi.fetchArchiveMonth(market, month.get(Calendar.YEAR), month.get(Calendar.MONTH) + 1)
        if (images == null && month.before(monthsAgo(2))) {
            // No file for a month that should have one: we've gone past the archive's start.
            exhausted = true
        }
        month.add(Calendar.MONTH, -1)
        return images.orEmpty()
    }

    /** The month containing the oldest image so far, or this month. */
    private fun startingArchiveMonth(): Calendar = Calendar.getInstance().apply {
        oldestDate?.let {
            set(it.substring(0, 4).toInt(), it.substring(4, 6).toInt() - 1, 1)
        } ?: set(Calendar.DAY_OF_MONTH, 1)
    }

    private fun monthsAgo(months: Int): Calendar = Calendar.getInstance().apply {
        set(Calendar.DAY_OF_MONTH, 1)
        add(Calendar.MONTH, -months)
    }
}
