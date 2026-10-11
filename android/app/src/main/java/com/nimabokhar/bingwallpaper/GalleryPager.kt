package com.nimabokhar.bingwallpaper

/**
 * Pages backwards through Bing's own feed of images of the day for one market.
 * Bing serves about the last 15 days in two pages. Not thread-safe; call
 * [nextPage] from one coroutine at a time.
 */
class GalleryPager(private val market: String) {
    private val offsets = mutableListOf(0, BingApi.MAX_OFFSET)
    private val seenDates = mutableSetOf<String>()

    val exhausted get() = offsets.isEmpty()

    /** The next, older batch of images, newest first. Blocks on the network. */
    fun nextPage(): List<BingImage> {
        val offset = offsets.first()
        val page = BingApi.fetchLatest(market, BingApi.MAX_IMAGES, offset)
        offsets.removeAt(0)
        // The pages overlap by a day; drop images already shown.
        return page.filter { seenDates.add(it.startDate) }
    }
}
