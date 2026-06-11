package com.example.ai_assistant_app

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.res.AssetManager
import android.util.Log
import java.nio.LongBuffer
import kotlin.math.sqrt

/**
 * EmbeddingService — Singleton that runs all-MiniLM-L6-v2 on Android via ONNX Runtime.
 *
 * Architecture:
 *   • Model:       all-MiniLM-L6-v2.onnx  (assets/, ~22 MB)
 *   • Vocab:       vocab.txt               (assets/, ~230 KB – BERT uncased vocab)
 *   • Inference:   onnxruntime-android AAR (native ARM64/ARMv7)
 *   • Tokenizer:   Inline WordPiece in Kotlin — no extra native dependency
 *   • Output:      FloatArray[384], L2-normalised sentence embedding
 *
 * Python accesses this from Chaquopy via the Java bridge:
 *   from java import jclass
 *   svc = jclass('com.example.ai_assistant_app.EmbeddingService').INSTANCE
 *   embedding_java = svc.embed(text)          # -> Java FloatArray
 *   embedding = list(embedding_java)          # -> Python list[float]
 */
object EmbeddingService {

    private const val TAG        = "EmbeddingService"
    private const val MAX_SEQ   = 128
    private const val EMB_DIM   = 384

    private var ortEnv : OrtEnvironment? = null
    private var session: OrtSession?     = null
    private var tokenizer: BertTokenizer? = null

    @Volatile var isReady = false
        private set

    // ─────────────────────────────────────────────────────────────────────────
    // Initialisation (called from BackendService.onCreate)
    // ─────────────────────────────────────────────────────────────────────────

    @Synchronized
    fun initialize(assets: AssetManager) {
        if (isReady) return
        try {
            Log.i(TAG, "Loading ONNX model (all-MiniLM-L6-v2)…")
            val modelBytes = assets.open("all-MiniLM-L6-v2.onnx").readBytes()
            ortEnv  = OrtEnvironment.getEnvironment()
            session = ortEnv!!.createSession(modelBytes, OrtSession.SessionOptions())

            Log.i(TAG, "Loading BERT vocab…")
            tokenizer = BertTokenizer.fromAssets(assets)

            isReady = true
            Log.i(TAG, "EmbeddingService ready ✓")
        } catch (e: Exception) {
            Log.e(TAG, "EmbeddingService init failed: ${e.message}", e)
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Public API — callable from Kotlin and Python (Chaquopy Java bridge)
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Returns a 384-dim L2-normalised FloatArray for [text], or null on error.
     * Safe to call from any thread.
     */
    fun embed(text: String): FloatArray? {
        val sess = session ?: run { Log.w(TAG, "Not initialised"); return null }
        val tok  = tokenizer ?: return null

        return try {
            val (inputIds, attMask, typeIds) = tok.encode(text, MAX_SEQ)
            val seqLen = inputIds.size.toLong()

            val idsTensor = OnnxTensor.createTensor(
                ortEnv!!, LongBuffer.wrap(inputIds), longArrayOf(1, seqLen))
            val maskTensor = OnnxTensor.createTensor(
                ortEnv!!, LongBuffer.wrap(attMask), longArrayOf(1, seqLen))
            val typeTensor = OnnxTensor.createTensor(
                ortEnv!!, LongBuffer.wrap(typeIds), longArrayOf(1, seqLen))

            val inputs = mapOf(
                "input_ids"      to idsTensor,
                "attention_mask" to maskTensor,
                "token_type_ids" to typeTensor
            )

            val result = sess.run(inputs)

            // last_hidden_state shape: [1, seqLen, 384]
            @Suppress("UNCHECKED_CAST")
            val hidden = (result[0].value as Array<Array<FloatArray>>)[0]

            // Mean pooling (attention-mask weighted)
            val emb = FloatArray(EMB_DIM)
            var count = 0
            for (i in 0 until seqLen.toInt()) {
                if (attMask[i] == 1L) {
                    for (j in 0 until EMB_DIM) emb[j] += hidden[i][j]
                    count++
                }
            }
            if (count > 0) for (j in 0 until EMB_DIM) emb[j] /= count.toFloat()

            // L2 normalise
            var norm = 0f
            for (v in emb) norm += v * v
            norm = sqrt(norm)
            if (norm > 0f) for (j in 0 until EMB_DIM) emb[j] /= norm

            idsTensor.close(); maskTensor.close(); typeTensor.close(); result.close()
            emb
        } catch (e: Exception) {
            Log.e(TAG, "embed() error: ${e.message}", e)
            null
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Inner: pure-Kotlin BERT WordPiece tokenizer
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Lightweight BERT uncased WordPiece tokenizer.
     * Loads vocabulary from assets/vocab.txt (one token per line, index = line number).
     */
    class BertTokenizer(private val vocab: Map<String, Int>) {

        private val unkId = vocab["[UNK]"] ?: 100
        private val clsId = vocab["[CLS]"] ?: 101
        private val sepId = vocab["[SEP]"] ?: 102
        private val padId = vocab["[PAD]"] ?: 0

        companion object {
            fun fromAssets(assets: AssetManager): BertTokenizer {
                val vocab = mutableMapOf<String, Int>()
                assets.open("vocab.txt").bufferedReader().useLines { lines ->
                    lines.forEachIndexed { idx, line -> vocab[line.trim()] = idx }
                }
                return BertTokenizer(vocab)
            }
        }

        /** Returns (input_ids, attention_mask, token_type_ids) all padded to [maxLen]. */
        fun encode(text: String, maxLen: Int = 128): Triple<LongArray, LongArray, LongArray> {
            val tokens = mutableListOf<Int>(clsId)

            for (word in basicTokenize(text)) {
                for (id in wordpiece(word)) {
                    if (tokens.size >= maxLen - 1) break
                    tokens.add(id)
                }
                if (tokens.size >= maxLen - 1) break
            }
            tokens.add(sepId)

            val inputIds = LongArray(maxLen) { i ->
                if (i < tokens.size) tokens[i].toLong() else padId.toLong()
            }
            val attMask = LongArray(maxLen) { i -> if (i < tokens.size) 1L else 0L }
            val typeIds = LongArray(maxLen) { 0L }

            return Triple(inputIds, attMask, typeIds)
        }

        /** Lowercase + whitespace/punctuation split, strip accents. */
        private fun basicTokenize(text: String): List<String> {
            val sb = StringBuilder()
            for (ch in text.lowercase()) {
                when {
                    ch.isWhitespace() -> sb.append(' ')
                    isPunctuation(ch) -> sb.append(' ').append(ch).append(' ')
                    ch.category == CharCategory.NON_SPACING_MARK -> { /* strip accents */ }
                    else -> sb.append(ch)
                }
            }
            return sb.split(Regex("\\s+")).filter { it.isNotBlank() }
        }

        /** WordPiece split for a single word. */
        private fun wordpiece(word: String): List<Int> {
            if (word.length > 200) return listOf(unkId)
            // Whole word in vocab?
            vocab[word]?.let { return listOf(it) }

            val result = mutableListOf<Int>()
            var start = 0
            while (start < word.length) {
                var end = word.length
                var bestId: Int? = null
                while (start < end) {
                    val sub = if (start == 0) word.substring(0, end)
                              else           "##${word.substring(start, end)}"
                    bestId = vocab[sub]
                    if (bestId != null) break
                    end--
                }
                if (bestId == null) return listOf(unkId)
                result.add(bestId)
                start = end
            }
            return result
        }

        private fun isPunctuation(c: Char): Boolean =
            c in '!'..'/' || c in ':'..'@' || c in '['..'`' || c in '{'..'~'
    }
}
