package com.fatheratum.omniterminal

import android.app.Activity
import android.os.Bundle
import android.view.WindowManager

class MainActivity : Activity() {
    private var pty:PtyProcess?=null

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        window.setSoftInputMode(
            WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        )
        setContentView(R.layout.activity_main)
        val terminal=findViewById<TerminalView>(R.id.terminalView)
        terminal.requestFocus()
        pty=PtyProcess(this)
        terminal.attachProcess(pty!!)
        pty!!.start()
    }

    override fun onDestroy() {
        pty?.stop()
        pty=null
        super.onDestroy()
    }
}
