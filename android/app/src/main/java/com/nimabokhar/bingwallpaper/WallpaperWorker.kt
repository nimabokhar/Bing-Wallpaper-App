package com.nimabokhar.bingwallpaper

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * Changes the wallpaper once a day at the time the user picked. Each run
 * schedules the next one, so the time never drifts. WorkManager keeps the
 * pending run across reboots.
 */
class WallpaperWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val followUps = inputData.getInt(KEY_FOLLOW_UPS, 0)
        try {
            val newest = BingApi.fetchImageOfTheDay(Settings.market(applicationContext))
            val applied = WallpaperSetter.applyNewest(applicationContext, force = false, image = newest)
            Log.i(TAG, if (applied != null) "Applied ${applied.id}" else "Already up to date")

            val publishedToday = newest.startDate == SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())
            if (!publishedToday && followUps < MAX_FOLLOW_UPS) {
                // Bing hasn't published today's image for this region yet; look again soon.
                enqueueNext(applicationContext, TimeUnit.HOURS.toMillis(1), followUps + 1)
            } else {
                enqueueNext(applicationContext, millisUntilScheduledTime(applicationContext), 0)
            }
            Result.success()
        } catch (e: Exception) {
            Log.w(TAG, "Wallpaper update failed", e)
            if (runAttemptCount < 3) {
                Result.retry()
            } else {
                // Give up for today, but keep the daily schedule going. The run must
                // succeed, or the next run chained after it would be cancelled too.
                enqueueNext(applicationContext, millisUntilScheduledTime(applicationContext), 0)
                Result.success()
            }
        }
    }

    companion object {
        private const val TAG = "WallpaperWorker"
        private const val WORK_NAME = "scheduled-bing-wallpaper"
        private const val LEGACY_PERIODIC_WORK_NAME = "daily-bing-wallpaper"
        private const val KEY_FOLLOW_UPS = "follow_ups"
        private const val MAX_FOLLOW_UPS = 6

        /**
         * Schedules the next automatic change at the user's chosen time. With
         * [replace] false an already pending run is kept, so calling this on every
         * app start doesn't push the schedule back.
         */
        fun schedule(context: Context, replace: Boolean) {
            val workManager = WorkManager.getInstance(context)
            workManager.cancelUniqueWork(LEGACY_PERIODIC_WORK_NAME)
            workManager.enqueueUniqueWork(
                WORK_NAME,
                if (replace) ExistingWorkPolicy.REPLACE else ExistingWorkPolicy.KEEP,
                request(millisUntilScheduledTime(context), 0),
            )
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }

        /** Called from a running worker: queues the next run behind the current one. */
        private fun enqueueNext(context: Context, delayMillis: Long, followUps: Int) {
            WorkManager.getInstance(context)
                .enqueueUniqueWork(WORK_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request(delayMillis, followUps))
        }

        private fun request(delayMillis: Long, followUps: Int) =
            OneTimeWorkRequestBuilder<WallpaperWorker>()
                .setInitialDelay(delayMillis, TimeUnit.MILLISECONDS)
                .setInputData(workDataOf(KEY_FOLLOW_UPS to followUps))
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()

        /** Milliseconds until the next occurrence of the chosen time of day. */
        fun millisUntilScheduledTime(context: Context, now: Calendar = Calendar.getInstance()): Long {
            val (hour, minute) = Settings.scheduleTime(context)
            val next = (now.clone() as Calendar).apply {
                set(Calendar.HOUR_OF_DAY, hour)
                set(Calendar.MINUTE, minute)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
                if (!after(now)) add(Calendar.DAY_OF_MONTH, 1)
            }
            return next.timeInMillis - now.timeInMillis
        }
    }
}
