package com.nimabokhar.bingwallpaper

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.lifecycle.LifecycleCoroutineScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/**
 * The main screen's list: the [header] (today's image and settings), then a grid
 * of images, then a footer line. Thumbnails come from [ImageLoader], decoded at
 * [thumbWidth] pixels wide, so binding a cell on the main thread is just setting
 * a ready bitmap.
 */
class GalleryAdapter(
    private val header: View,
    private val scope: LifecycleCoroutineScope,
    private val thumbWidth: Int,
    private val formatDate: (String) -> String,
    private val onImageClick: (BingImage) -> Unit,
    private val onFooterClick: () -> Unit,
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val images = mutableListOf<BingImage>()
    private val thumbHeight = (thumbWidth * ThumbnailFrame.HEIGHT_RATIO).toInt()

    var footerText: CharSequence = ""
        set(value) {
            if (field == value) return
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
        if (more.isEmpty()) return
        val start = 1 + images.size
        images += more
        notifyItemRangeInserted(start, more.size)
    }

    /** Header and footer span the whole row; images take one column each. */
    fun spanSizeLookup(columns: Int) = object : GridLayoutManager.SpanSizeLookup() {
        override fun getSpanSize(position: Int) = if (getItemViewType(position) == TYPE_IMAGE) 1 else columns
    }.apply { isSpanIndexCacheEnabled = true }

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
            val titleText = image.title.ifBlank { image.copyright }
            val dateText = formatDate(image.startDate)
            title.text = titleText
            date.text = dateText
            itemView.contentDescription = "$titleText, $dateText"
            itemView.setOnClickListener { onImageClick(image) }

            val urls = thumbnailUrls(image)
            val cached = ImageLoader.cached(urls, thumbWidth, thumbHeight)
            if (cached != null) {
                thumb.setImageBitmap(cached)
                return
            }
            job = scope.launch {
                val bitmap = ImageLoader.load(itemView.context, urls, thumbWidth, thumbHeight) ?: return@launch
                fadeIn(thumb, bitmap)
            }
        }

        fun unbind() {
            job?.cancel()
            job = null
            thumb.animate().cancel()
            thumb.alpha = 1f
            thumb.setImageDrawable(null)
        }
    }

    companion object {
        private const val TYPE_HEADER = 0
        private const val TYPE_IMAGE = 1
        private const val TYPE_FOOTER = 2

        fun thumbnailUrls(image: BingImage) = listOf(image.thumbnailUrl, image.fallbackUrl)
    }
}

/** Shows a freshly loaded [bitmap] with a short fade, so images don't pop in. */
fun fadeIn(view: ImageView, bitmap: android.graphics.Bitmap) {
    view.alpha = 0f
    view.setImageBitmap(bitmap)
    view.animate().alpha(1f).setDuration(180).start()
}
