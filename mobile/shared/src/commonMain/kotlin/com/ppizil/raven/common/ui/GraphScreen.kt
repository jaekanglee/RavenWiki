package com.ppizil.raven.common.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material.CircularProgressIndicator
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.pow
import kotlin.math.sqrt
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.PI
import kotlin.math.min

private val WIKILINK_PATTERN = Regex("""\[\[([^\]|]+)(?:\|[^\]]+)?\]\]""")

private class GraphNode(val doc: Document, var x: Float, var y: Float)
private data class GraphEdge(val from: Int, val to: Int)
private data class GraphData(
    val nodes: List<GraphNode>,
    val edges: List<GraphEdge>,
    val connectedIndices: Set<Int>,
)

private fun buildGraphData(documents: List<Document>): GraphData {
    val slugIndex = documents.mapIndexed { i, doc -> doc.id.lowercase() to i }.toMap()
    val titleIndex = documents.mapIndexed { i, doc -> doc.title.lowercase() to i }.toMap()

    val nodes = documents.mapIndexed { i, doc ->
        val angle = 2.0 * PI * i / documents.size
        GraphNode(
            doc = doc,
            x = 0.5f + 0.35f * cos(angle).toFloat(),
            y = 0.5f + 0.35f * sin(angle).toFloat(),
        )
    }

    val edges = mutableListOf<GraphEdge>()
    val seen = mutableSetOf<Pair<Int, Int>>()

    documents.forEachIndexed { fromIdx, doc ->
        WIKILINK_PATTERN.findAll(doc.content).forEach { match ->
            val target = match.groupValues[1].trim().lowercase()
            val toIdx = slugIndex[target] ?: titleIndex[target]
            if (toIdx != null && toIdx != fromIdx) {
                val edge = if (fromIdx < toIdx) fromIdx to toIdx else toIdx to fromIdx
                if (seen.add(edge)) {
                    edges.add(GraphEdge(edge.first, edge.second))
                }
            }
        }
    }

    val iterations = min(20, 800 / (nodes.size.coerceAtLeast(1)))
    if (nodes.size > 1) {
        repeat(iterations.coerceAtLeast(5)) {
            for (i in nodes.indices) {
                for (j in i + 1 until nodes.size) {
                    val dx = nodes[i].x - nodes[j].x
                    val dy = nodes[i].y - nodes[j].y
                    val dist = sqrt(dx * dx + dy * dy).coerceAtLeast(0.01f)
                    val repulsion = 0.002f / (dist * dist)
                    val fx = dx / dist * repulsion
                    val fy = dy / dist * repulsion
                    nodes[i].x += fx
                    nodes[i].y += fy
                    nodes[j].x -= fx
                    nodes[j].y -= fy
                }
            }
            for (edge in edges) {
                val a = nodes[edge.from]
                val b = nodes[edge.to]
                val dx = b.x - a.x
                val dy = b.y - a.y
                val dist = sqrt(dx * dx + dy * dy).coerceAtLeast(0.01f)
                val attraction = dist * 0.1f
                val fx = dx / dist * attraction
                val fy = dy / dist * attraction
                a.x += fx
                a.y += fy
                b.x -= fx
                b.y -= fy
            }
            for (node in nodes) {
                node.x += (0.5f - node.x) * 0.05f
                node.y += (0.5f - node.y) * 0.05f
                node.x = node.x.coerceIn(0.05f, 0.95f)
                node.y = node.y.coerceIn(0.05f, 0.95f)
            }
        }
    }

    val connectedIndices = edges.flatMap { listOf(it.from, it.to) }.toSet()
    return GraphData(nodes, edges, connectedIndices)
}

@Composable
fun GraphScreen(
    documents: List<Document>,
    onNodeClick: (Document) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        if (documents.isEmpty()) {
            Text("문서가 없어 그래프를 그릴 수 없습니다.", style = MaterialTheme.typography.body1)
        } else {
            var graphData by remember { mutableStateOf<GraphData?>(null) }

            LaunchedEffect(documents) {
                graphData = withContext(Dispatchers.Default) {
                    buildGraphData(documents)
                }
            }

            val data = graphData
            if (data == null) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "그래프 계산 중…",
                        style = MaterialTheme.typography.caption,
                        color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                    )
                }
            } else {
                val nodeColor = MaterialTheme.colors.primary
                val isolatedColor = MaterialTheme.colors.onSurface.copy(alpha = 0.3f)
                val edgeColor = MaterialTheme.colors.onSurface.copy(alpha = 0.15f)

                var scale by remember { mutableStateOf(1f) }
                var offset by remember { mutableStateOf(Offset.Zero) }
                var canvasSize by remember { mutableStateOf(androidx.compose.ui.geometry.Size.Zero) }

                Canvas(
                    modifier = Modifier
                        .fillMaxSize()
                        .pointerInput(Unit) {
                            detectTransformGestures { _, pan, zoom, _ ->
                                scale = (scale * zoom).coerceIn(0.5f, 5f)
                                offset += pan
                            }
                        }
                        .pointerInput("tap") {
                            detectTapGestures { tapOffset ->
                                if (canvasSize != androidx.compose.ui.geometry.Size.Zero) {
                                    val graphTap = (tapOffset - offset) / scale
                                    val radius = 30f / scale

                                    val clickedNode = data.nodes.find { node ->
                                        val nodeX = node.x * canvasSize.width
                                        val nodeY = node.y * canvasSize.height
                                        val dist = sqrt(
                                            (graphTap.x - nodeX).pow(2) + (graphTap.y - nodeY).pow(2),
                                        )
                                        dist <= radius
                                    }
                                    if (clickedNode != null) {
                                        onNodeClick(clickedNode.doc)
                                    }
                                }
                            }
                        },
                ) {
                    canvasSize = size
                    val w = size.width
                    val h = size.height

                    withTransform({
                        translate(offset.x, offset.y)
                        scale(scale, scale, Offset.Zero)
                    }) {
                        for (edge in data.edges) {
                            val a = data.nodes[edge.from]
                            val b = data.nodes[edge.to]
                            drawLine(
                                color = edgeColor,
                                start = Offset(a.x * w, a.y * h),
                                end = Offset(b.x * w, b.y * h),
                                strokeWidth = 1.5f / scale,
                            )
                        }

                        data.nodes.forEachIndexed { idx, node ->
                            val color = if (idx in data.connectedIndices) nodeColor else isolatedColor
                            val nodeRadius = if (idx in data.connectedIndices) 14f / scale else 8f / scale
                            drawCircle(
                                color = color,
                                radius = nodeRadius,
                                center = Offset(node.x * w, node.y * h),
                            )
                        }
                    }
                }

                Column(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        "문서 ${documents.size}개 · 연결 ${data.edges.size}개",
                        style = MaterialTheme.typography.caption,
                        color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                    )
                    Text(
                        "핀치로 확대, 드래그로 이동, 탭하여 열기",
                        style = MaterialTheme.typography.caption,
                        color = MaterialTheme.colors.onSurface.copy(alpha = 0.4f),
                    )
                }
            }
        }
    }
}
