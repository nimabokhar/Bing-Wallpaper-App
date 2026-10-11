package com.nimabokhar.bingwallpaper

import android.app.AlertDialog
import android.os.Bundle
import android.text.format.DateUtils
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.Switch
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.text.SimpleDateFormat
import java.util.Locale

class MainActivity : ComponentActivity() {

    private lateinit var gallery: LinearLayout
    private lateinit var galleryMessage: TextView
    private lateinit var setNow: Button
    private lateinit var status: TextView
    private var galleryJob: Job? = null
    private var settingWallpaper = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        gallery = findViewById(R.id.gallery)
        galleryMessage = findViewById(R.id.galleryMessage)
        setNow = findViewById(R.id.setNow)
        status = findViewById(R.id.status)

        val dailySwitch = findViewById<Switch>(R.id.dailySwitch)
        dailySwitch.isChecked = Settings.isDailyEnabled(this)
        dailySwitch.setOnCheckedChangeListener { _, checked -> Settings.setDailyEnabled(this, checked) }

        setNow.setOnClickListener { setTodayNow() }

        setUpRegionPicker()
        showLastApplied()
        loadGallery()
    }

    private fun setUpRegionPicker() {
        val deviceMarket = BingApi.deviceMarket()
        val deviceName = BingApi.MARKETS.first { it.first == deviceMarket }.second
        // Index 0 follows the device; the rest map to BingApi.MARKETS in order.
        val labels = listOf(getString(R.string.region_automatic, deviceName)) + BingApi.MARKETS.map { it.second }
        val spinner = findViewById<Spinner>(R.id.regionSpinner)
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, labels)

        val chosen = Settings.chosenMarket(this)
        val chosenIndex = BingApi.MARKETS.indexOfFirst { it.first == chosen }
        spinner.setSelection(if (chosenIndex >= 0) chosenIndex + 1 else 0, false)

        spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val market = if (position == 0) null else BingApi.MARKETS[position - 1].first
                if (market == Settings.chosenMarket(this@MainActivity)) return
                Settings.setChosenMarket(this@MainActivity, market)
                loadGallery()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    private fun loadGallery() {
        galleryJob?.cancel()
        gallery.removeAllViews()
        galleryMessage.setText(R.string.loading)
        galleryJob = lifecycleScope.launch {
            val images = try {
                withContext(Dispatchers.IO) { BingApi.fetchLatest(Settings.market(applicationContext)) }
            } catch (e: Exception) {
                galleryMessage.setText(R.string.load_failed)
                return@launch
            }
            galleryMessage.setText(R.string.gallery_hint)

            // Two images per row.
            val thumbs = images.chunked(2).flatMap { pair ->
                val row = LinearLayout(this@MainActivity).apply { orientation = LinearLayout.HORIZONTAL }
                gallery.addView(row)
                val views = pair.map { image -> addItem(row, image) }
                // Keep an odd last image at half width.
                if (pair.size == 1) row.addView(View(this@MainActivity), LinearLayout.LayoutParams(0, 0, 1f))
                views
            }

            for ((image, thumb) in images.zip(thumbs)) {
                launch {
                    withContext(Dispatchers.IO) { BingApi.downloadThumbnail(image) }?.let(thumb::setImageBitmap)
                }
            }
        }
    }

    /** Adds a gallery item for [image] to [row] and returns its thumbnail view. */
    private fun addItem(row: LinearLayout, image: BingImage): ImageView {
        val item = layoutInflater.inflate(R.layout.item_image, row, false)
        item.findViewById<TextView>(R.id.itemTitle).text = image.title.ifBlank { image.copyright }
        item.findViewById<TextView>(R.id.itemDate).text = formatDate(image.startDate)
        item.setOnClickListener { chooseTarget(image) }
        row.addView(item)
        return item.findViewById(R.id.thumb)
    }

    private fun chooseTarget(image: BingImage) {
        if (settingWallpaper) return
        val targets = WallpaperTarget.entries
        val labels = targets.map {
            getString(
                when (it) {
                    WallpaperTarget.BOTH -> R.string.target_both
                    WallpaperTarget.HOME -> R.string.target_home
                    WallpaperTarget.LOCK -> R.string.target_lock
                }
            )
        }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.set_where, image.title.ifBlank { formatDate(image.startDate) }))
            .setItems(labels) { _, which -> setWallpaper { WallpaperSetter.apply(applicationContext, image, targets[which]); image } }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun setTodayNow() {
        setWallpaper { WallpaperSetter.applyNewest(applicationContext, force = true)!! }
    }

    private fun setWallpaper(action: () -> BingImage) {
        if (settingWallpaper) return
        settingWallpaper = true
        setNow.isEnabled = false
        status.setText(R.string.setting)
        lifecycleScope.launch {
            try {
                val image = withContext(Dispatchers.IO) {
                    // Picking an image by hand counts as handling today's image, so the
                    // daily update leaves it alone until Bing publishes a newer one.
                    val newest = BingApi.fetchImageOfTheDay(Settings.market(applicationContext))
                    action().also { WallpaperSetter.markNewestSeen(applicationContext, newest.id) }
                }
                status.text = getString(R.string.set_done, image.title)
            } catch (e: Exception) {
                status.text = getString(R.string.set_failed, e.message ?: e.javaClass.simpleName)
            } finally {
                settingWallpaper = false
                setNow.isEnabled = true
            }
        }
    }

    private fun showLastApplied() {
        val last = WallpaperSetter.lastApplied(this)
        status.text = if (last == null) {
            getString(R.string.never_applied)
        } else {
            val whenText = DateUtils.getRelativeTimeSpanString(last.second)
            getString(R.string.last_applied, "${last.first} ($whenText)")
        }
    }

    private fun formatDate(yyyyMMdd: String): String = runCatching {
        val date = SimpleDateFormat("yyyyMMdd", Locale.US).parse(yyyyMMdd)!!
        DateFormat.getDateInstance(DateFormat.MEDIUM).format(date)
    }.getOrDefault(yyyyMMdd)
}
