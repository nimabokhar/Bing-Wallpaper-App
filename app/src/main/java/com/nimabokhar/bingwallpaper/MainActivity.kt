package com.nimabokhar.bingwallpaper

import android.os.Bundle
import android.text.format.DateUtils
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ImageView
import android.widget.Spinner
import android.widget.Switch
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var preview: ImageView
    private lateinit var titleView: TextView
    private lateinit var copyright: TextView
    private lateinit var setNow: Button
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        preview = findViewById(R.id.preview)
        titleView = findViewById(R.id.title)
        copyright = findViewById(R.id.copyright)
        setNow = findViewById(R.id.setNow)
        status = findViewById(R.id.status)

        val dailySwitch = findViewById<Switch>(R.id.dailySwitch)
        dailySwitch.isChecked = Settings.isDailyEnabled(this)
        dailySwitch.setOnCheckedChangeListener { _, checked -> Settings.setDailyEnabled(this, checked) }

        setNow.setOnClickListener { setWallpaperNow() }

        setUpRegionPicker()

        showLastApplied()
        loadPreview()
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
                loadPreview()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    private fun loadPreview() {
        titleView.setText(R.string.loading)
        copyright.text = ""
        lifecycleScope.launch {
            try {
                val (image, bitmap) = withContext(Dispatchers.IO) {
                    val image = BingApi.fetchImageOfTheDay(Settings.market(applicationContext))
                    image to BingApi.downloadBitmap(image)
                }
                preview.setImageBitmap(bitmap)
                titleView.text = image.title
                copyright.text = image.copyright
            } catch (e: Exception) {
                titleView.setText(R.string.load_failed)
            }
        }
    }

    private fun setWallpaperNow() {
        setNow.isEnabled = false
        status.setText(R.string.setting)
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) { WallpaperSetter.applyToday(applicationContext, force = true) }
                status.setText(R.string.set_done)
            } catch (e: Exception) {
                status.text = getString(R.string.set_failed, e.message ?: e.javaClass.simpleName)
            } finally {
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
}
