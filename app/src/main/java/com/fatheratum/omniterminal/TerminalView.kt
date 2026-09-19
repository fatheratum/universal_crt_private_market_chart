package com.fatheratum.omniterminal

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.view.KeyEvent
import android.view.View

class TerminalView(context: Context) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = Typeface.MONOSPACE
        textSize = 28f
    }

    private val buffer = StringBuilder()
    private var terminalProcess: PtyProcess? = null

    init {
        isFocusable = true
        isFocusableInTouchMode = true
        setBackgroundColor(0xFF000000.toInt())
    }

    fun attachProcess(process: PtyProcess) {
        terminalProcess = process
        process.onOutput = { text ->
            post {
                buffer.append(text)
                if (buffer.length > 20000) {
                    buffer.delete(0, buffer.length - 20000)
                }
                invalidate()
            }
        }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val lines = buffer.toString().split("\n")
        var y = 34f
        val lineHeight = 34f

        for (line in lines.takeLast(height / lineHeight.toInt().coerceAtLeast(1))) {
            canvas.drawText(line.take(240), 8f, y, paint)
            y += lineHeight
            if (y > height) break
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        terminalProcess?.writeKey(event)
        return true
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        return true
    }

    override fun onCheckIsTextEditor(): Boolean = true
}
