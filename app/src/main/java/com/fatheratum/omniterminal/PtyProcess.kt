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

    fun start() {
        executor.execute {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(context))
                }

                val py = Python.getInstance()
                module = py.getModule("omni_runner")

                module!!.callAttr(
                    "prepare",
                    context.filesDir.absolutePath
                )

                val script = File(
                    context.filesDir,
                    "universal_crt_v4.py"
                )

                context.assets.open("universal_crt_v4.py").use { input ->
                    script.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }

                module!!.callAttr(
                    "start",
                    script.absolutePath,
                    112,
                    32
                )

                while (!stopped) {
                    val output =
                        module!!.callAttr("read_output").toString()

                    if (output.isNotEmpty()) {
                        onOutput?.invoke(output)
                    }

                    if (
                        module!!
                            .callAttr("running")
                            .toString()
                            .toBoolean()
                            .not()
                    ) {
                        break
                    }

                    Thread.sleep(50)
                }
            } catch (t: Throwable) {
                onOutput?.invoke(
                    "\n[ANDROID PYTHON ERROR] " +
                    "${t.javaClass.simpleName}: ${t.message}\n"
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
        } catch (_: Throwable) {
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
