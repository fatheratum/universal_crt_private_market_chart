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
        textSize = 22f
    }

    private var frame = ""
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
                frame = text
                    .replace(Regex("\u001B\\[[0-9;?]*[ -/]*[@-~]"), "")
                    .replace("\u001B", "")
                    .replace("\r", "")

                invalidate()
            }
        }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val lines = frame.split("\n")
        val lineHeight = 24f
        var y = 24f

        for (line in lines) {
            if (y > height) break

            canvas.drawText(
                line.take(240),
                8f,
                y,
                paint
            )

            y += lineHeight
        }
    }

    override fun onKeyDown(
        keyCode: Int,
        event: KeyEvent
    ): Boolean {
        terminalProcess?.writeKey(event)
        return true
    }

    override fun onKeyUp(
        keyCode: Int,
        event: KeyEvent
    ): Boolean {
        return true
    }

    override fun onCheckIsTextEditor(): Boolean = true
}
