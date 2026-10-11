package com.nimabokhar.bingwallpaper

import android.os.Bundle
import android.text.format.DateUtils
import android.widget.Button
import android.widget.ImageView
import android.widget.Switch
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var preview: ImageView
    private lateinit var title: TextView
    private lateinit var copyright: TextView
    private lateinit var setNow: Button
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        preview = findViewById(R.id.preview)
        title = findViewById(R.id.title)
        copyright = findViewById(R.id.copyright)
        setNow = findViewById(R.id.setNow)
        status = findViewById(R.id.status)

        val dailySwitch = findViewById<Switch>(R.id.dailySwitch)
        dailySwitch.isChecked = Settings.isDailyEnabled(this)
        dailySwitch.setOnCheckedChangeListener { _, checked -> Settings.setDailyEnabled(this, checked) }

        setNow.setOnClickListener { setWallpaperNow() }

        showLastApplied()
        loadPreview()
    }

    private fun loadPreview() {
        lifecycleScope.launch {
            try {
                val (image, bitmap) = withContext(Dispatchers.IO) {
                    val image = BingApi.fetchImageOfTheDay()
                    image to BingApi.downloadBitmap(image)
                }
                preview.setImageBitmap(bitmap)
                title.text = image.title
                copyright.text = image.copyright
            } catch (e: Exception) {
                title.setText(R.string.load_failed)
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
