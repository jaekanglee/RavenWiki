package com.ppizil.raven.common.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document
import kotlin.random.Random
import kotlin.math.pow
import kotlin.math.sqrt

@Composable
fun GraphScreen(
    documents: List<Document>,
    onNodeClick: (Document) -> Unit = {},
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        if (documents.isEmpty()) {
            Text("No documents to form a graph.", style = MaterialTheme.typography.body1)
        } else {
            val nodeColor = MaterialTheme.colors.primary
            val edgeColor = MaterialTheme.colors.onSurface.copy(alpha = 0.2f)
            
            var scale by remember { mutableStateOf(1f) }
            var offset by remember { mutableStateOf(Offset.Zero) }
            var canvasSize by remember { mutableStateOf(androidx.compose.ui.geometry.Size.Zero) }
            
            val nodes = remember(documents) {
                documents.take(50).map { doc ->
                    Pair(doc, Offset(Random.nextFloat(), Random.nextFloat()))
                }
            }
            
            val edges = remember(nodes) {
                val edgeList = mutableListOf<Pair<Int, Int>>()
                for (i in nodes.indices) {
                    for (j in i + 1 until nodes.size) {
                        if (Random.nextFloat() > 0.90f) { 
                            edgeList.add(Pair(i, j))
                        }
                    }
                }
                edgeList
            }
            
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
                                val radius = 25f / scale // Node click radius
                                
                                val clickedNode = nodes.find { (_, pos) ->
                                    val nodeX = pos.x * canvasSize.width
                                    val nodeY = pos.y * canvasSize.height
                                    val dist = sqrt((graphTap.x - nodeX).pow(2) + (graphTap.y - nodeY).pow(2))
                                    dist <= radius
                                }
                                if (clickedNode != null) {
                                    onNodeClick(clickedNode.first)
                                }
                            }
                        }
                    }
            ) {
                canvasSize = size
                val canvasWidth = size.width
                val canvasHeight = size.height
                
                withTransform({
                    translate(offset.x, offset.y)
                    scale(scale, scale, Offset.Zero)
                }) {
                    for ((i, j) in edges) {
                        val start = nodes[i].second
                        val end = nodes[j].second
                        drawLine(
                            color = edgeColor,
                            start = Offset(start.x * canvasWidth, start.y * canvasHeight),
                            end = Offset(end.x * canvasWidth, end.y * canvasHeight),
                            strokeWidth = 2f / scale
                        )
                    }
                    
                    nodes.forEach { (_, normalizedPos) ->
                        drawCircle(
                            color = nodeColor,
                            radius = 20f / scale,
                            center = Offset(normalizedPos.x * canvasWidth, normalizedPos.y * canvasHeight)
                        )
                    }
                }
            }
            
            Column(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("Knowledge Graph", style = MaterialTheme.typography.subtitle1, color = MaterialTheme.colors.primary)
                Text("Pinch to zoom, drag to pan, tap to open", style = MaterialTheme.typography.caption)
            }
        }
    }
}
