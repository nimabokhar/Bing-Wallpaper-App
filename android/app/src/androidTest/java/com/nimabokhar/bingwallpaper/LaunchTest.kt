package com.nimabokhar.bingwallpaper

import android.view.View
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Opens the app on a real (emulated) device and pokes at it. Any crash, on the
 * main thread or in a coroutine, kills the process and fails the test. CI runs
 * it on a phone-sized screen and again on a Z Fold-sized unfolded screen.
 */
@RunWith(AndroidJUnit4::class)
class LaunchTest {
    @Test
    fun opensLoadsAndSurvivesRecreation() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            assertEquals(Lifecycle.State.RESUMED, scenario.state)
            // Give the first page of images and today's image time to load.
            Thread.sleep(8_000)

            scenario.onActivity { it.findViewById<View>(R.id.settingsButton).performClick() }
            Thread.sleep(1_000)

            // Folding or unfolding a foldable recreates the activity.
            scenario.recreate()
            Thread.sleep(3_000)
            assertEquals(Lifecycle.State.RESUMED, scenario.state)
        }
    }
}
