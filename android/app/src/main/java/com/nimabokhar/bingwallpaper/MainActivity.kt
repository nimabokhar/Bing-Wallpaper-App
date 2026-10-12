package com.nimabokhar.bingwallpaper

import android.content.res.Configuration
import android.os.Bundle
import android.text.format.DateUtils
import android.view.View
import android.widget.ImageView
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updateLayoutParams
import androidx.core.view.updatePadding
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.recyclerview.widget.SimpleItemAnimator
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.button.MaterialButton
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.android.material.materialswitch.MaterialSwitch
import com.google.android.material.progressindicator.CircularProgressIndicator
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.textfield.MaterialAutoCompleteTextView
import com.google.android.material.timepicker.MaterialTimePicker
import com.google.android.material.timepicker.TimeFormat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import kotlin.math.roundToInt

class MainActivity : AppCompatActivity() {

    private lateinit var header: View
    private lateinit var gallery: RecyclerView
    private lateinit var galleryLayout: GridLayoutManager
    private lateinit var adapter: GalleryAdapter
    private lateinit var galleryMessage: TextView
    private lateinit var statusScrim: View
    private var pager: GalleryPager? = null
    private var firstPageLoaded = false
    private var loadingMore = false
    private var loadFailed = false
    private lateinit var setNow: MaterialButton
    private lateinit var status: TextView
    private lateinit var setProgress: LinearProgressIndicator
    private var galleryJob: Job? = null
    private var settingWallpaper = false

    private lateinit var hero: View
    private lateinit var heroImage: ImageView
    private lateinit var heroProgress: CircularProgressIndicator
    private lateinit var heroDate: TextView
    private lateinit var heroTitle: TextView
    private lateinit var heroCaption: TextView
    private var heroWidth = 0
    private var heroHeight = 0
    private var heroJob: Job? = null
    private var today: BingImage? = null

    /** Whether the status bar currently sits over the page rather than over the hero image. */
    private var barsOverPage: Boolean? = null
    private var openSheet: BottomSheetDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        // Folding or unfolding recreates the activity, so this sees every screen.
        ScreenShapes.recordCurrent(this)

        gallery = findViewById(R.id.gallery)
        statusScrim = findViewById(R.id.statusScrim)

        // Big landscape cards: one per row on a phone, more on wide windows such as
        // an unfolded foldable or a tablet.
        val columns = (resources.configuration.screenWidthDp / 360).coerceIn(1, 4)
        galleryLayout = GridLayoutManager(this, columns)
        // The layout manager must be in place before anything is inflated into the
        // RecyclerView: it supplies the layout params, and without it inflating throws.
        gallery.layoutManager = galleryLayout
        header = layoutInflater.inflate(R.layout.gallery_header, gallery, false)
        val spacing = resources.getDimensionPixelSize(R.dimen.grid_spacing)
        val screenWidth = resources.displayMetrics.widthPixels
        val thumbWidth = (screenWidth - spacing * (columns + 1)) / columns
        adapter = GalleryAdapter(header, lifecycleScope, thumbWidth, ::formatDate, ::chooseTarget) {
            if (loadFailed) {
                loadFailed = false
                loadMore()
            }
        }
        galleryLayout.spanSizeLookup = adapter.spanSizeLookup(columns)
        gallery.adapter = adapter
        // The list always fills the screen, so adding images never re-measures it.
        gallery.setHasFixedSize(true)
        gallery.addItemDecoration(GridSpacing(spacing))
        // Keep a couple of rows of cells bound just off screen, ready to scroll back to.
        gallery.setItemViewCacheSize(columns * 2)
        // The header is a single shared view, so it must never be duplicated for a change animation.
        (gallery.itemAnimator as? SimpleItemAnimator)?.supportsChangeAnimations = false
        gallery.addOnScrollListener(object : RecyclerView.OnScrollListener() {
            override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                if (dy > 0) loadFailed = false
                maybeLoadMore()
                updateStatusBar()
            }
        })

        setUpHero()
        setUpDailyCard()
        applyWindowInsets()
        updateStatusBar()
        showLastApplied()
        loadGallery()
    }

    override fun onDestroy() {
        openSheet?.dismiss()
        super.onDestroy()
    }

    private fun setUpHero() {
        hero = header.findViewById(R.id.hero)
        heroImage = header.findViewById(R.id.heroImage)
        heroProgress = header.findViewById(R.id.heroProgress)
        heroDate = header.findViewById(R.id.heroDate)
        heroTitle = header.findViewById(R.id.heroTitle)
        heroCaption = header.findViewById(R.id.heroCaption)
        setNow = header.findViewById(R.id.setNow)

        // Fixed from the window size, so the hero never changes height while loading.
        val metrics = resources.displayMetrics
        heroWidth = metrics.widthPixels
        heroHeight = minOf((metrics.widthPixels * 1.2f).roundToInt(), (metrics.heightPixels * 0.62f).roundToInt())
        hero.updateLayoutParams { height = heroHeight }
        roundCorners(hero, resources.getDimension(R.dimen.hero_corner), bottomOnly = true)

        hero.setOnClickListener {
            val image = today
            when {
                image != null -> chooseTarget(image)
                loadFailed -> loadGallery()
            }
        }
        setNow.setOnClickListener { setTodayNow() }
        header.findViewById<View>(R.id.settingsButton).setOnClickListener { showSettings() }
    }

    private fun showHero(image: BingImage?) {
        today = image
        heroJob?.cancel()
        heroImage.animate().cancel()
        heroImage.alpha = 1f
        heroImage.setImageDrawable(null)
        if (image == null) {
            heroDate.text = ""
            heroTitle.setText(R.string.loading)
            heroCaption.text = ""
            heroProgress.visibility = View.VISIBLE
            return
        }
        val isToday = image.startDate == SimpleDateFormat("yyyyMMdd", Locale.US).format(Calendar.getInstance().time)
        heroDate.text = if (isToday) getString(R.string.today, formatDate(image.startDate)) else formatDate(image.startDate)
        heroTitle.text = image.title.ifBlank { image.copyright }
        heroCaption.text = if (image.title.isBlank()) "" else image.copyright
        hero.contentDescription = heroTitle.text

        // Bing's portrait crop suits a tall hero, its landscape one a wide hero.
        val shape = if (heroWidth >= heroHeight) ImageResolution.FULL_HD else ImageResolution.PORTRAIT
        val urls = listOf(image.urlBase + shape.suffix, image.fallbackUrl)
        val cached = ImageLoader.cached(urls, heroWidth, heroHeight)
        if (cached != null) {
            heroProgress.visibility = View.GONE
            heroImage.setImageBitmap(cached)
            return
        }
        heroProgress.visibility = View.VISIBLE
        heroJob = lifecycleScope.launch {
            val bitmap = ImageLoader.load(this@MainActivity, urls, heroWidth, heroHeight)
            heroProgress.visibility = View.GONE
            if (bitmap != null) fadeIn(heroImage, bitmap)
        }
    }

    private fun setUpDailyCard() {
        status = header.findViewById(R.id.status)
        setProgress = header.findViewById(R.id.setProgress)
        galleryMessage = header.findViewById(R.id.galleryMessage)

        val dailySwitch = header.findViewById<MaterialSwitch>(R.id.dailySwitch)
        val scheduleRow = header.findViewById<View>(R.id.scheduleRow)
        val scheduleValue = header.findViewById<TextView>(R.id.scheduleValue)
        dailySwitch.isChecked = Settings.isDailyEnabled(this)
        fun showSchedule() {
            val (hour, minute) = Settings.scheduleTime(this)
            scheduleValue.text = formatTime(hour, minute)
            scheduleRow.isEnabled = dailySwitch.isChecked
            scheduleRow.alpha = if (dailySwitch.isChecked) 1f else 0.38f
        }
        fun listenTo(picker: MaterialTimePicker) {
            picker.addOnPositiveButtonClickListener {
                Settings.setScheduleTime(this, picker.hour, picker.minute)
                showSchedule()
            }
        }
        // A picker left open across a rotation comes back without its listener.
        (supportFragmentManager.findFragmentByTag(TIME_PICKER) as? MaterialTimePicker)?.let(::listenTo)
        scheduleRow.setOnClickListener {
            val (hour, minute) = Settings.scheduleTime(this)
            val is24Hour = android.text.format.DateFormat.is24HourFormat(this)
            val picker = MaterialTimePicker.Builder()
                .setTimeFormat(if (is24Hour) TimeFormat.CLOCK_24H else TimeFormat.CLOCK_12H)
                .setHour(hour)
                .setMinute(minute)
                .setTitleText(R.string.schedule_label)
                .build()
            listenTo(picker)
            picker.show(supportFragmentManager, TIME_PICKER)
        }
        dailySwitch.setOnCheckedChangeListener { _, checked ->
            Settings.setDailyEnabled(this, checked)
            showSchedule()
        }
        showSchedule()
    }

    /** Draws behind the system bars and pads the content just enough to clear them. */
    private fun applyWindowInsets() {
        val heroTop = header.findViewById<View>(R.id.settingsButton)
        val heroTopMargin = (heroTop.layoutParams as ViewGroupMarginParams).topMargin
        val bottomPadding = gallery.paddingBottom
        ViewCompat.setOnApplyWindowInsetsListener(gallery) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            view.updatePadding(left = bars.left, right = bars.right, bottom = bottomPadding + bars.bottom)
            statusScrim.updateLayoutParams { height = bars.top }
            heroTop.updateLayoutParams<ViewGroupMarginParams> { topMargin = heroTopMargin + bars.top }
            insets
        }
    }

    /**
     * Light status bar icons over the hero image; once it scrolls away, fade in a
     * solid bar behind them and switch to the theme's icon colour.
     */
    private fun updateStatusBar() {
        val heroBottom = when (galleryLayout.findFirstVisibleItemPosition()) {
            RecyclerView.NO_POSITION -> Int.MAX_VALUE // Not laid out yet: at the top.
            0 -> header.top + hero.bottom
            else -> 0
        }
        val overPage = heroBottom <= statusScrim.height
        if (overPage == barsOverPage) return
        val firstTime = barsOverPage == null
        barsOverPage = overPage
        val night = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = overPage && !night
        val alpha = if (overPage) 1f else 0f
        if (firstTime) statusScrim.alpha = alpha else statusScrim.animate().alpha(alpha).setDuration(150).start()
    }

    private fun showSettings() {
        val sheet = BottomSheetDialog(this)
        val view = layoutInflater.inflate(R.layout.sheet_settings, null)
        sheet.setContentView(view)
        view.findViewById<TextView>(R.id.version).text = getString(R.string.version, BuildConfig.VERSION_NAME)

        // Region: index 0 follows the device; the rest map to BingApi.MARKETS in order.
        val deviceMarket = BingApi.deviceMarket()
        val deviceName = BingApi.MARKETS.first { it.first == deviceMarket }.second
        val regions = listOf(getString(R.string.region_automatic, deviceName)) + BingApi.MARKETS.map { it.second }
        val chosenIndex = BingApi.MARKETS.indexOfFirst { it.first == Settings.chosenMarket(this) }
        view.findViewById<MaterialAutoCompleteTextView>(R.id.regionMenu).apply {
            setSimpleItems(regions.toTypedArray())
            setText(regions[if (chosenIndex >= 0) chosenIndex + 1 else 0], false)
            setOnItemClickListener { _, _, position, _ ->
                val market = if (position == 0) null else BingApi.MARKETS[position - 1].first
                if (market == Settings.chosenMarket(this@MainActivity)) return@setOnItemClickListener
                Settings.setChosenMarket(this@MainActivity, market)
                loadGallery()
            }
        }

        // Same order as ImageResolution.
        val resolutions = listOf(
            R.string.resolution_uhd, R.string.resolution_full_hd, R.string.resolution_hd, R.string.resolution_portrait,
        ).map(::getString)
        view.findViewById<MaterialAutoCompleteTextView>(R.id.resolutionMenu).apply {
            setSimpleItems(resolutions.toTypedArray())
            setText(resolutions[Settings.resolution(this@MainActivity).ordinal], false)
            setOnItemClickListener { _, _, position, _ ->
                Settings.setResolution(this@MainActivity, ImageResolution.entries[position])
            }
        }

        // Same order as ThemeMode.
        val themeButtons = listOf(R.id.themeSystem, R.id.themeLight, R.id.themeDark)
        view.findViewById<MaterialButtonToggleGroup>(R.id.themeGroup).apply {
            check(themeButtons[Settings.themeMode(this@MainActivity).ordinal])
            addOnButtonCheckedListener { _, id, checked ->
                if (!checked) return@addOnButtonCheckedListener
                val mode = ThemeMode.entries[themeButtons.indexOf(id)]
                if (mode == Settings.themeMode(this@MainActivity)) return@addOnButtonCheckedListener
                Settings.setThemeMode(this@MainActivity, mode)
                sheet.dismiss()
                // Recreates the activity in the new theme; images come back from the cache.
                AppCompatDelegate.setDefaultNightMode(mode.nightMode)
            }
        }
        show(sheet)
    }

    private fun show(sheet: BottomSheetDialog) {
        openSheet?.dismiss()
        openSheet = sheet
        sheet.setOnDismissListener { if (openSheet === sheet) openSheet = null }
        sheet.show()
    }

    private fun loadGallery() {
        galleryJob?.cancel()
        adapter.setImages(emptyList())
        adapter.footerText = ""
        pager = GalleryPager(Settings.market(applicationContext))
        firstPageLoaded = false
        loadingMore = false
        loadFailed = false
        galleryMessage.setText(R.string.loading)
        showHero(null)
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
        val firstPage = !firstPageLoaded
        if (!firstPage) adapter.footerText = getString(R.string.loading_more)
        galleryJob = lifecycleScope.launch {
            try {
                val images = withContext(Dispatchers.IO) { pager.nextPage() }
                // The newest image is the hero; the grid shows the ones before it.
                val forGrid = if (firstPage) {
                    firstPageLoaded = true
                    galleryMessage.setText(R.string.gallery_hint)
                    showHero(images.firstOrNull())
                    images.drop(1)
                } else {
                    images
                }
                adapter.addImages(forGrid)
                ImageLoader.prefetch(this@MainActivity, forGrid.map(GalleryAdapter::thumbnailUrls))
                adapter.footerText = if (pager.exhausted) getString(R.string.gallery_end) else ""
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                if (firstPage) {
                    galleryMessage.setText(R.string.load_failed)
                    heroProgress.visibility = View.GONE
                    heroTitle.setText(R.string.load_failed_retry)
                }
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
        val sheet = BottomSheetDialog(this)
        val view = layoutInflater.inflate(R.layout.sheet_target, null)
        sheet.setContentView(view)
        view.findViewById<TextView>(R.id.targetTitle).text =
            getString(R.string.set_where, image.title.ifBlank { formatDate(image.startDate) })
        mapOf(
            R.id.targetBoth to WallpaperTarget.BOTH,
            R.id.targetHome to WallpaperTarget.HOME,
            R.id.targetLock to WallpaperTarget.LOCK,
        ).forEach { (id, target) ->
            view.findViewById<View>(id).setOnClickListener {
                sheet.dismiss()
                setWallpaper { WallpaperSetter.apply(applicationContext, image, target); image }
            }
        }
        show(sheet)
    }

    private fun setTodayNow() {
        setWallpaper { WallpaperSetter.applyNewest(applicationContext, force = true)!! }
    }

    private fun setWallpaper(action: () -> BingImage) {
        if (settingWallpaper) return
        settingWallpaper = true
        setNow.isEnabled = false
        setProgress.visibility = View.VISIBLE
        status.setText(R.string.setting)
        lifecycleScope.launch {
            try {
                val image = withContext(Dispatchers.IO) {
                    // Picking an image by hand counts as handling today's image, so the
                    // daily update leaves it alone until Bing publishes a newer one.
                    val newest = BingApi.fetchImageOfTheDay(Settings.market(applicationContext))
                    action().also { WallpaperSetter.markNewestSeen(applicationContext, newest.id) }
                }
                showLastApplied()
                Snackbar.make(gallery, getString(R.string.set_done, image.title), Snackbar.LENGTH_SHORT).show()
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                val message = getString(R.string.set_failed, e.message ?: e.javaClass.simpleName)
                status.text = message
                Snackbar.make(gallery, message, Snackbar.LENGTH_LONG).show()
            } finally {
                settingWallpaper = false
                setNow.isEnabled = true
                setProgress.visibility = View.INVISIBLE
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

    private companion object {
        const val TIME_PICKER = "time_picker"
    }
}

private typealias ViewGroupMarginParams = android.view.ViewGroup.MarginLayoutParams
