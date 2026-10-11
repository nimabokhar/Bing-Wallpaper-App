package com.nimabokhar.bingwallpaper

import android.content.Context
import android.graphics.Outline
import android.graphics.Rect
import android.util.AttributeSet
import android.view.View
import android.view.ViewOutlineProvider
import android.widget.FrameLayout
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlin.math.roundToInt

/**
 * A gallery cell: rounded corners and a fixed landscape shape, so its height
 * comes from its width alone and loading an image never resizes it. The corners
 * are clipped with an outline, which the GPU does for free.
 */
class ThumbnailFrame @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : FrameLayout(context, attrs) {
    init {
        roundCorners(this, resources.getDimension(R.dimen.thumb_corner))
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        super.onMeasure(
            MeasureSpec.makeMeasureSpec(width, MeasureSpec.EXACTLY),
            MeasureSpec.makeMeasureSpec((width * HEIGHT_RATIO).roundToInt(), MeasureSpec.EXACTLY),
        )
    }

    companion object {
        /** Height / width of a cell: 16:9, the shape of Bing's images. */
        const val HEIGHT_RATIO = 9f / 16f
    }
}

/** Clips [view] to a rounded rectangle; with [bottomOnly], only the bottom corners are rounded. */
fun roundCorners(view: View, radius: Float, bottomOnly: Boolean = false) {
    view.outlineProvider = object : ViewOutlineProvider() {
        override fun getOutline(view: View, outline: Outline) {
            val top = if (bottomOnly) -radius.roundToInt() else 0
            outline.setRoundRect(0, top, view.width, view.height, radius)
        }
    }
    view.clipToOutline = true
}

/** Even gaps around and between grid cells. Full-width rows (header, footer) are left alone. */
class GridSpacing(private val spacing: Int) : RecyclerView.ItemDecoration() {
    override fun getItemOffsets(outRect: Rect, view: View, parent: RecyclerView, state: RecyclerView.State) {
        val params = view.layoutParams as? GridLayoutManager.LayoutParams ?: return
        val columns = (parent.layoutManager as? GridLayoutManager)?.spanCount ?: return
        if (params.spanSize != 1) return
        val column = params.spanIndex
        outRect.left = spacing - column * spacing / columns
        outRect.right = (column + 1) * spacing / columns
        outRect.bottom = spacing
    }
}
