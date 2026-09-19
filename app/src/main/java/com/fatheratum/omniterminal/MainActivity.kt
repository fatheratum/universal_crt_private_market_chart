package com.fatheratum.omniterminal

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.WindowManager
import android.widget.TextView
import android.widget.ScrollView

class MainActivity : Activity() {
    private var pty: PtyProcess? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        requestedOrientation =
            android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE

        window.setSoftInputMode(
            WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        )

        val terminal = TerminalView(this)

        val scroll = ScrollView(this)
        scroll.setBackgroundColor(Color.BLACK)
        scroll.addView(terminal)
        setContentView(scroll)

        try {
            pty = PtyProcess(this)
            terminal.attachProcess(pty!!)
            terminal.showBootMessage("UNIVERSAL CRT V4\nStarting Python runtime...")
            pty!!.start()
        } catch (t: Throwable) {
            showFatalError(t)
        }
    }

    private fun showFatalError(t: Throwable) {
        val error = TextView(this)
        error.setTextColor(Color.WHITE)
        error.setBackgroundColor(Color.BLACK)
        error.textSize = 16f
        error.setPadding(20, 20, 20, 20)
        error.text =
            "UNIVERSAL CRT STARTUP FAILURE\n\n" +
            t.javaClass.name + "\n\n" +
            (t.message ?: "NO MESSAGE") + "\n\n" +
            t.stackTraceToString()

        val scroll = ScrollView(this)
        scroll.setBackgroundColor(Color.BLACK)
        scroll.addView(error)
        setContentView(scroll)
    }

    override fun onDestroy() {
        try {
            pty?.stop()
        } catch (_: Throwable) {
        }
        pty = null
        super.onDestroy()
    }
}
