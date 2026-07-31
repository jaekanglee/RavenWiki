package com.ppizil.raven.common.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.ClickableText
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.Divider
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ppizil.raven.common.domain.model.Document

private sealed class MdBlock {
    data class Heading(val level: Int, val text: String) : MdBlock()
    data class Paragraph(val text: String) : MdBlock()
    data class CodeBlock(val code: String) : MdBlock()
    data class ListItem(val text: String, val indent: Int) : MdBlock()
    object HorizontalRule : MdBlock()
}

private fun parseMarkdownBlocks(content: String): List<MdBlock> {
    val blocks = mutableListOf<MdBlock>()
    val lines = content.lines()
    var i = 0
    var paragraphBuffer = StringBuilder()

    fun flushParagraph() {
        if (paragraphBuffer.isNotBlank()) {
            blocks.add(MdBlock.Paragraph(paragraphBuffer.toString().trim()))
        }
        paragraphBuffer = StringBuilder()
    }

    while (i < lines.size) {
        val line = lines[i]
        when {
            line.startsWith("```") -> {
                flushParagraph()
                val codeLines = mutableListOf<String>()
                i++
                while (i < lines.size && !lines[i].startsWith("```")) {
                    codeLines.add(lines[i])
                    i++
                }
                blocks.add(MdBlock.CodeBlock(codeLines.joinToString("\n")))
            }
            line.matches(Regex("^#{1,6}\\s+.*")) -> {
                flushParagraph()
                val level = line.takeWhile { it == '#' }.length
                blocks.add(MdBlock.Heading(level, line.drop(level).trim()))
            }
            line.matches(Regex("^\\s*[-*+]\\s+.*")) -> {
                flushParagraph()
                val indent = line.takeWhile { it == ' ' }.length / 2
                val text = line.trimStart().drop(2)
                blocks.add(MdBlock.ListItem(text, indent))
            }
            line.matches(Regex("^\\s*\\d+\\.\\s+.*")) -> {
                flushParagraph()
                val indent = line.takeWhile { it == ' ' }.length / 2
                val text = line.trimStart().replaceFirst(Regex("^\\d+\\.\\s+"), "")
                blocks.add(MdBlock.ListItem(text, indent))
            }
            line.matches(Regex("^-{3,}$|^\\*{3,}$|^_{3,}$")) -> {
                flushParagraph()
                blocks.add(MdBlock.HorizontalRule)
            }
            line.isBlank() -> {
                flushParagraph()
            }
            else -> {
                if (paragraphBuffer.isNotEmpty()) paragraphBuffer.append(" ")
                paragraphBuffer.append(line)
            }
        }
        i++
    }
    flushParagraph()
    return blocks
}

private val INLINE_CODE = Regex("`([^`]+)`")
private val BOLD = Regex("\\*\\*(.+?)\\*\\*|__(.+?)__")
private val ITALIC = Regex("\\*(.+?)\\*|_(.+?)_")
private val WIKILINK = Regex("\\[\\[([^\\]|]+)(?:\\|([^\\]]+))?\\]\\]")

private const val WIKILINK_TAG = "wikilink"

private fun buildInlineAnnotated(
    text: String,
    primaryColor: androidx.compose.ui.graphics.Color,
): AnnotatedString {
    return buildAnnotatedString {
        var remaining = text
        while (remaining.isNotEmpty()) {
            val codeMatch = INLINE_CODE.find(remaining)
            val boldMatch = BOLD.find(remaining)
            val italicMatch = ITALIC.find(remaining)
            val wikiMatch = WIKILINK.find(remaining)

            val earliest = listOfNotNull(codeMatch, boldMatch, italicMatch, wikiMatch)
                .minByOrNull { it.range.first }

            if (earliest == null) {
                append(remaining)
                break
            }

            if (earliest.range.first > 0) {
                append(remaining.substring(0, earliest.range.first))
            }

            when (earliest) {
                codeMatch -> withStyle(SpanStyle(fontFamily = FontFamily.Monospace)) {
                    append(earliest.groupValues[1])
                }
                boldMatch -> withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                    append(earliest.groupValues[1].ifEmpty { earliest.groupValues[2] })
                }
                italicMatch -> withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
                    append(earliest.groupValues[1].ifEmpty { earliest.groupValues[2] })
                }
                wikiMatch -> {
                    val target = earliest.groupValues[1]
                    val label = earliest.groupValues[2].ifEmpty { target }
                    pushStringAnnotation(tag = WIKILINK_TAG, annotation = target)
                    withStyle(SpanStyle(color = primaryColor, fontWeight = FontWeight.Medium)) {
                        append(label)
                    }
                    pop()
                }
            }

            remaining = remaining.substring(earliest.range.last + 1)
        }
    }
}

@Composable
private fun InlineMarkdownText(
    text: String,
    style: TextStyle,
    modifier: Modifier = Modifier,
    onWikilinkClick: ((String) -> Unit)? = null,
) {
    val primaryColor = MaterialTheme.colors.primary
    val annotated = remember(text) { buildInlineAnnotated(text, primaryColor) }

    if (onWikilinkClick != null) {
        ClickableText(
            text = annotated,
            style = style.copy(color = MaterialTheme.colors.onSurface),
            modifier = modifier,
            onClick = { offset ->
                annotated.getStringAnnotations(tag = WIKILINK_TAG, start = offset, end = offset)
                    .firstOrNull()
                    ?.let { annotation -> onWikilinkClick(annotation.item) }
            },
        )
    } else {
        Text(text = annotated, style = style, modifier = modifier)
    }
}

private fun formatTimestamp(millis: Long): String {
    if (millis <= 0L) return ""
    val seconds = millis / 1000
    val minutes = seconds / 60
    val hours = minutes / 60
    val days = hours / 24

    val nowSeconds = io.ktor.util.date.getTimeMillis() / 1000
    val diffSeconds = nowSeconds - seconds

    return when {
        diffSeconds < 60 -> "방금 전"
        diffSeconds < 3600 -> "${diffSeconds / 60}분 전"
        diffSeconds < 86400 -> "${diffSeconds / 3600}시간 전"
        diffSeconds < 604800 -> "${diffSeconds / 86400}일 전"
        else -> {
            val totalDays = days
            val year = 1970 + (totalDays / 365).toInt()
            val month = ((totalDays % 365) / 30).toInt() + 1
            val day = ((totalDays % 365) % 30).toInt() + 1
            "${year}. ${month}. ${day}."
        }
    }
}

@Composable
fun DocumentDetailScreen(
    document: Document,
    onWikilinkClick: ((String) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val blocks = remember(document.content) { parseMarkdownBlocks(document.content) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text(
            text = document.title,
            style = MaterialTheme.typography.h5,
            color = MaterialTheme.colors.onSurface,
            fontWeight = FontWeight.Bold,
        )

        val meta = buildList {
            document.type?.takeIf { it.isNotBlank() }?.let { add(it) }
            val ts = formatTimestamp(document.lastUpdated)
            if (ts.isNotEmpty()) add(ts)
        }
        if (meta.isNotEmpty()) {
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = meta.joinToString(" · "),
                style = MaterialTheme.typography.caption,
                color = MaterialTheme.colors.onSurface.copy(alpha = 0.5f),
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        blocks.forEach { block ->
            when (block) {
                is MdBlock.Heading -> {
                    Spacer(modifier = Modifier.height(12.dp))
                    InlineMarkdownText(
                        text = block.text,
                        style = when (block.level) {
                            1 -> MaterialTheme.typography.h5
                            2 -> MaterialTheme.typography.h6
                            3 -> MaterialTheme.typography.subtitle1.copy(fontWeight = FontWeight.Bold)
                            else -> MaterialTheme.typography.subtitle2.copy(fontWeight = FontWeight.Bold)
                        },
                        onWikilinkClick = onWikilinkClick,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
                is MdBlock.Paragraph -> {
                    InlineMarkdownText(
                        text = block.text,
                        style = MaterialTheme.typography.body1,
                        onWikilinkClick = onWikilinkClick,
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                }
                is MdBlock.CodeBlock -> {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = block.code,
                        style = MaterialTheme.typography.body2.copy(
                            fontFamily = FontFamily.Monospace,
                            fontSize = 13.sp,
                        ),
                        color = MaterialTheme.colors.onSurface.copy(alpha = 0.85f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
                is MdBlock.ListItem -> {
                    Row(modifier = Modifier.padding(start = (block.indent * 16 + 8).dp)) {
                        Text("•  ", style = MaterialTheme.typography.body1)
                        InlineMarkdownText(
                            text = block.text,
                            style = MaterialTheme.typography.body1,
                            modifier = Modifier.weight(1f),
                            onWikilinkClick = onWikilinkClick,
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                }
                is MdBlock.HorizontalRule -> {
                    Spacer(modifier = Modifier.height(8.dp))
                    Divider()
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}
