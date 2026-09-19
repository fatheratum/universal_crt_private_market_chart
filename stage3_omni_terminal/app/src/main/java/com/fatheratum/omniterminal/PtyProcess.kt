package com.fatheratum.omniterminal

import android.view.KeyEvent
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.concurrent.Executors

class PtyProcess(private val context: android.content.Context) {
    var onOutput: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor()
    private var stdin: java.io.OutputStream? = null
    private var process: Process? = null

    fun start() {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context))
        }

        executor.execute {
            try {
                val py = Python.getInstance()
                val module = py.getModule("omni_runner")
                module.callAttr("prepare", context.filesDir.absolutePath)

                val script = java.io.File(
                    context.filesDir,
                    "universal_crt_v4.py"
                )

                val source = context.assets.open("universal_crt_v4.py")
                    .bufferedReader()
                    .use { it.readText() }

                script.writeText(source)

                val command = arrayOf(
                    "sh",
                    "-c",
                    "exec python3 " + script.absolutePath
                )

                process = ProcessBuilder(*command)
                    .redirectErrorStream(true)
                    .start()

                stdin = process!!.outputStream

                BufferedReader(
                    InputStreamReader(process!!.inputStream)
                ).forEachLine { line ->
                    onOutput?.invoke(line + "\n")
                }
            } catch (t: Throwable) {
                onOutput?.invoke(
                    "\n[PTY ERROR] ${t.javaClass.simpleName}: ${t.message}\n"
                )
            }
        }
    }

    fun writeKey(event: KeyEvent) {
        val out = stdin ?: return

        try {
            val text = event.unicodeChar
            if (text != 0) {
                out.write(byteArrayOf(text.toByte()))
            } else {
                when (event.keyCode) {
                    KeyEvent.KEYCODE_ENTER -> out.write('\n'.code)
                    KeyEvent.KEYCODE_DEL -> out.write(127)
                    KeyEvent.KEYCODE_DPAD_UP -> out.write("\u001B[A".toByteArray())
                    KeyEvent.KEYCODE_DPAD_DOWN -> out.write("\u001B[B".toByteArray())
                    KeyEvent.KEYCODE_DPAD_RIGHT -> out.write("\u001B[C".toByteArray())
                    KeyEvent.KEYCODE_DPAD_LEFT -> out.write("\u001B[D".toByteArray())
                    KeyEvent.KEYCODE_TAB -> out.write('\t'.code)
                    KeyEvent.KEYCODE_ESCAPE -> out.write(27)
                }
            }
            out.flush()
        } catch (_: Throwable) {
        }
    }

    fun stop() {
        try {
            stdin?.close()
        } catch (_: Throwable) {
        }

        process?.destroy()
        executor.shutdownNow()
    }
}
