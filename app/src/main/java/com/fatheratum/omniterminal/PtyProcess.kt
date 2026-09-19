package com.fatheratum.omniterminal

import android.content.Context
import android.view.KeyEvent
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.util.concurrent.Executors

class PtyProcess(private val context: Context) {
    var onOutput: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor()

    private var module: com.chaquo.python.PyObject? = null

    @Volatile
    private var stopped = false

    private fun output(text: String) {
        onOutput?.invoke(text)
    }

    fun start() {
        output(
            "UNIVERSAL CRT V4\n" +
            "ANDROID RUNTIME STARTING...\n"
        )

        executor.execute {
            try {
                output("1. EXECUTOR OK\n")

                if (!Python.isStarted()) {
                    output("2. STARTING CHAQUOPY...\n")
                    Python.start(AndroidPlatform(context))
                }

                output("3. CHAQUOPY OK\n")

                val py = Python.getInstance()

                output("4. PYTHON INSTANCE OK\n")

                module = py.getModule("omni_runner")

                output("5. omni_runner IMPORTED\n")

                module!!.callAttr(
                    "prepare",
                    context.filesDir.absolutePath
                )

                output("6. RUNNER PREPARED\n")

                val script = File(
                    context.filesDir,
                    "universal_crt_v4.py"
                )

                context.assets.open("universal_crt_v4.py").use { input ->
                    script.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }

                output("7. CRT SCRIPT COPIED\n")

                module!!.callAttr(
                    "start",
                    script.absolutePath,
                    112,
                    32
                )

                output("8. PYTHON CRT THREAD STARTED\n")

                while (!stopped) {
                    val result =
                        module!!.callAttr("read_output").toString()

                    if (result.isNotEmpty()) {
                        output(result)
                    }

                    val running =
                        module!!
                            .callAttr("running")
                            .toString()
                            .toBoolean()

                    if (!running) {
                        output(
                            "\nPYTHON CRT STOPPED.\n"
                        )
                        break
                    }

                    Thread.sleep(50)
                }
            } catch (t: Throwable) {
                output(
                    "\n\n=== ANDROID RUNTIME ERROR ===\n" +
                    t.javaClass.name +
                    "\n\n" +
                    (t.message ?: "NO MESSAGE") +
                    "\n\n" +
                    t.stackTraceToString()
                )
            }
        }
    }

    fun writeKey(event: KeyEvent) {
        val m = module ?: return

        try {
            when (event.keyCode) {
                KeyEvent.KEYCODE_DPAD_UP ->
                    m.callAttr("send_key", "UP")

                KeyEvent.KEYCODE_DPAD_DOWN ->
                    m.callAttr("send_key", "DOWN")

                KeyEvent.KEYCODE_DPAD_LEFT ->
                    m.callAttr("send_key", "LEFT")

                KeyEvent.KEYCODE_DPAD_RIGHT ->
                    m.callAttr("send_key", "RIGHT")

                KeyEvent.KEYCODE_ENTER ->
                    m.callAttr("send_key", "ENTER")

                KeyEvent.KEYCODE_DEL ->
                    m.callAttr("send_key", "\u007F")

                KeyEvent.KEYCODE_TAB ->
                    m.callAttr("send_key", "\t")

                KeyEvent.KEYCODE_ESCAPE ->
                    m.callAttr("send_key", "ESC")

                else -> {
                    val c = event.unicodeChar
                    if (c != 0) {
                        m.callAttr(
                            "send_key",
                            c.toChar().toString()
                        )
                    }
                }
            }
        } catch (t: Throwable) {
            output(
                "\n[KEY ERROR] ${t.javaClass.name}: ${t.message}\n"
            )
        }
    }

    fun stop() {
        stopped = true

        try {
            module?.callAttr("stop")
        } catch (_: Throwable) {
        }

        executor.shutdownNow()
    }
}
