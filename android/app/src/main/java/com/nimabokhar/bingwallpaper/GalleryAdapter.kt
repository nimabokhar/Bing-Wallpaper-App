package com.nimabokhar.bingwallpaper

import android.graphics.Bitmap
import android.util.LruCache
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.lifecycle.LifecycleCoroutineScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The main screen's list: the settings [header], then a grid of images, then a
 * footer line. Thumbnails are loaded as items come on screen and kept in a small
 * memory cache, so scrolling through hundreds of images stays light.
 */
class GalleryAdapter(
    private val header: View,
    private val scope: LifecycleCoroutineScope,
    private val formatDate: (String) -> String,
    private val onImageClick: (BingImage) -> Unit,
    private val onFooterClick: () -> Unit,
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val images = mutableListOf<BingImage>()
    private val thumbnails = object : LruCache<String, Bitmap>(cacheSizeKb()) {
        override fun sizeOf(key: String, value: Bitmap) = value.byteCount / 1024
    }

    var footerText: CharSequence = ""
        set(value) {
            field = value
            notifyItemChanged(itemCount - 1)
        }

    val imageCount get() = images.size

    fun setImages(newImages: List<BingImage>) {
        val old = images.size
        images.clear()
        notifyItemRangeRemoved(1, old)
        addImages(newImages)
    }

    fun addImages(more: List<BingImage>) {
        val start = 1 + images.size
        images += more
        notifyItemRangeInserted(start, more.size)
    }

    /** Header and footer span the whole row; images take one column each. */
    fun spanSizeLookup(columns: Int) = object : GridLayoutManager.SpanSizeLookup() {
        override fun getSpanSize(position: Int) = if (getItemViewType(position) == TYPE_IMAGE) 1 else columns
    }

    override fun getItemCount() = images.size + 2

    override fun getItemViewType(position: Int) = when (position) {
        0 -> TYPE_HEADER
        itemCount - 1 -> TYPE_FOOTER
        else -> TYPE_IMAGE
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return when (viewType) {
            TYPE_HEADER -> object : RecyclerView.ViewHolder(header) {}
            TYPE_FOOTER -> object : RecyclerView.ViewHolder(inflater.inflate(R.layout.gallery_footer, parent, false)) {}
                .also { holder -> holder.itemView.setOnClickListener { onFooterClick() } }
            else -> ImageHolder(inflater.inflate(R.layout.item_image, parent, false))
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        when (holder) {
            is ImageHolder -> holder.bind(images[position - 1])
            else -> if (getItemViewType(position) == TYPE_FOOTER) (holder.itemView as TextView).text = footerText
        }
    }

    override fun onViewRecycled(holder: RecyclerView.ViewHolder) {
        (holder as? ImageHolder)?.unbind()
    }

    private inner class ImageHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val thumb: ImageView = view.findViewById(R.id.thumb)
        private val title: TextView = view.findViewById(R.id.itemTitle)
        private val date: TextView = view.findViewById(R.id.itemDate)
        private var job: Job? = null

        fun bind(image: BingImage) {
            unbind()
            title.text = image.title.ifBlank { image.copyright }
            date.text = formatDate(image.startDate)
            itemView.setOnClickListener { onImageClick(image) }

            val cached = thumbnails.get(image.thumbnailUrl)
            thumb.setImageBitmap(cached)
            if (cached == null) {
                job = scope.launch {
                    val bitmap = withContext(Dispatchers.IO) { BingApi.downloadThumbnail(image) } ?: return@launch
                    thumbnails.put(image.thumbnailUrl, bitmap)
                    thumb.setImageBitmap(bitmap)
                }
            }
        }

        fun unbind() {
            job?.cancel()
            job = null
            thumb.setImageBitmap(null)
        }
    }

    companion object {
        private const val TYPE_HEADER = 0
        private const val TYPE_IMAGE = 1
        private const val TYPE_FOOTER = 2

        /** An eighth of the app's memory for thumbnails. */
        private fun cacheSizeKb() = (Runtime.getRuntime().maxMemory() / 1024 / 8).toInt()
    }
}
