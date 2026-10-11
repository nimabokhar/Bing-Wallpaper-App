package com.nimabokhar.bingwallpaper

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

class WallpaperWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val applied = WallpaperSetter.applyNewest(applicationContext, force = false)
            Log.i(TAG, if (applied != null) "Applied ${applied.id}" else "Already up to date")
            Result.success()
        } catch (e: Exception) {
            Log.w(TAG, "Wallpaper update failed", e)
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }

    companion object {
        private const val TAG = "WallpaperWorker"
        private const val WORK_NAME = "daily-bing-wallpaper"

        /**
         * Checks every few hours and only changes the wallpaper when Bing has a new
         * image, so the change lands soon after Bing publishes it each day.
         * WorkManager keeps this schedule across reboots.
         */
        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<WallpaperWorker>(4, TimeUnit.HOURS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.KEEP, request)
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
