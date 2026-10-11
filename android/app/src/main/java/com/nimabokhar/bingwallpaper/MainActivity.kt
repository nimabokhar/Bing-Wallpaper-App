package com.nimabokhar.bingwallpaper

import android.app.AlertDialog
import android.app.TimePickerDialog
import android.content.Context
import android.content.res.Configuration
import android.os.Bundle
import android.text.format.DateUtils
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.Switch
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.recyclerview.widget.SimpleItemAnimator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

class MainActivity : ComponentActivity() {

    private lateinit var header: View
    private lateinit var gallery: RecyclerView
    private lateinit var galleryLayout: GridLayoutManager
    private lateinit var adapter: GalleryAdapter
    private lateinit var galleryMessage: TextView
    private var pager: GalleryPager? = null
    private var loadingMore = false
    private var loadFailed = false
    private lateinit var setNow: Button
    private lateinit var status: TextView
    private var galleryJob: Job? = null
    private var settingWallpaper = false

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(newBase)
        // Force light or dark resources when the user overrides the system theme.
        val night = when (Settings.themeMode(newBase)) {
            ThemeMode.SYSTEM -> return
            ThemeMode.LIGHT -> Configuration.UI_MODE_NIGHT_NO
            ThemeMode.DARK -> Configuration.UI_MODE_NIGHT_YES
        }
        val uiMode = newBase.resources.configuration.uiMode
        applyOverrideConfiguration(Configuration().apply {
            this.uiMode = (uiMode and Configuration.UI_MODE_NIGHT_MASK.inv()) or night
        })
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        // Folding or unfolding recreates the activity, so this sees every screen.
        ScreenShapes.recordCurrent(this)

        gallery = findViewById(R.id.gallery)
        header = layoutInflater.inflate(R.layout.gallery_header, gallery, false)
        adapter = GalleryAdapter(header, lifecycleScope, ::formatDate, ::chooseTarget) {
            if (loadFailed) {
                loadFailed = false
                loadMore()
            }
        }
        // More columns on wide windows, such as an unfolded foldable or a tablet.
        val columns = (resources.configuration.screenWidthDp / 180).coerceIn(2, 5)
        galleryLayout = GridLayoutManager(this, columns).apply { spanSizeLookup = adapter.spanSizeLookup(columns) }
        gallery.layoutManager = galleryLayout
        gallery.adapter = adapter
        // The header is a single shared view, so it must never be duplicated for a change animation.
        (gallery.itemAnimator as? SimpleItemAnimator)?.supportsChangeAnimations = false
        gallery.addOnScrollListener(object : RecyclerView.OnScrollListener() {
            override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                if (dy > 0) loadFailed = false
                maybeLoadMore()
            }
        })

        galleryMessage = header.findViewById(R.id.galleryMessage)
        setNow = header.findViewById(R.id.setNow)
        status = header.findViewById(R.id.status)
        header.findViewById<TextView>(R.id.version).text = getString(R.string.version, BuildConfig.VERSION_NAME)

        val dailySwitch = header.findViewById<Switch>(R.id.dailySwitch)
        dailySwitch.isChecked = Settings.isDailyEnabled(this)
        val scheduleLabel = header.findViewById<TextView>(R.id.scheduleLabel)
        val scheduleButton = header.findViewById<Button>(R.id.scheduleButton)
        fun showSchedule() {
            val (hour, minute) = Settings.scheduleTime(this)
            scheduleButton.text = formatTime(hour, minute)
            scheduleButton.isEnabled = dailySwitch.isChecked
            scheduleLabel.isEnabled = dailySwitch.isChecked
        }
        scheduleButton.setOnClickListener {
            val (hour, minute) = Settings.scheduleTime(this)
            TimePickerDialog(this, { _, h, m ->
                Settings.setScheduleTime(this, h, m)
                showSchedule()
            }, hour, minute, android.text.format.DateFormat.is24HourFormat(this)).show()
        }
        dailySwitch.setOnCheckedChangeListener { _, checked ->
            Settings.setDailyEnabled(this, checked)
            showSchedule()
        }
        showSchedule()

        setNow.setOnClickListener { setTodayNow() }

        setUpRegionPicker()
        setUpThemePicker()
        showLastApplied()
        loadGallery()
    }

    private fun setUpRegionPicker() {
        val deviceMarket = BingApi.deviceMarket()
        val deviceName = BingApi.MARKETS.first { it.first == deviceMarket }.second
        // Index 0 follows the device; the rest map to BingApi.MARKETS in order.
        val labels = listOf(getString(R.string.region_automatic, deviceName)) + BingApi.MARKETS.map { it.second }
        val spinner = header.findViewById<Spinner>(R.id.regionSpinner)
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

    private fun setUpThemePicker() {
        val labels = listOf(R.string.theme_system, R.string.theme_light, R.string.theme_dark).map(::getString)
        val spinner = header.findViewById<Spinner>(R.id.themeSpinner)
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, labels)
        spinner.setSelection(Settings.themeMode(this).ordinal, false)
        spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val mode = ThemeMode.entries[position]
                if (mode == Settings.themeMode(this@MainActivity)) return
                Settings.setThemeMode(this@MainActivity, mode)
                recreate()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    private fun loadGallery() {
        galleryJob?.cancel()
        adapter.setImages(emptyList())
        adapter.footerText = ""
        pager = GalleryPager(Settings.market(applicationContext))
        loadingMore = false
        loadFailed = false
        galleryMessage.setText(R.string.loading)
        loadMore()
    }

    /** Loads the next, older page when the user nears the end of the gallery. */
    private fun maybeLoadMore() {
        val lastVisible = galleryLayout.findLastVisibleItemPosition()
        if (lastVisible >= adapter.itemCount - 1 - galleryLayout.spanCount * 3) loadMore()
    }

    private fun loadMore() {
        val pager = pager ?: return
        if (loadingMore || pager.exhausted || loadFailed) return
        loadingMore = true
        val firstPage = adapter.imageCount == 0
        if (!firstPage) adapter.footerText = getString(R.string.loading_more)
        galleryJob = lifecycleScope.launch {
            try {
                val images = withContext(Dispatchers.IO) { pager.nextPage() }
                if (firstPage) galleryMessage.setText(R.string.gallery_hint)
                adapter.addImages(images)
                adapter.footerText = if (pager.exhausted) getString(R.string.gallery_end) else ""
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                if (firstPage) galleryMessage.setText(R.string.load_failed)
                adapter.footerText = getString(R.string.load_more_failed)
                // Wait for the user to tap the footer or scroll before retrying.
                loadFailed = true
            } finally {
                // A region change may have replaced the pager while this page loaded.
                if (this@MainActivity.pager === pager) {
                    loadingMore = false
                    gallery.post { maybeLoadMore() }
                }
            }
        }
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

    private fun formatTime(hour: Int, minute: Int): String {
        val calendar = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, hour)
            set(Calendar.MINUTE, minute)
        }
        return android.text.format.DateFormat.getTimeFormat(this).format(calendar.time)
    }
}
