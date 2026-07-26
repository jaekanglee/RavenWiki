import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.ppizil.raven.common.ui.SlidingPanelLayout
import com.ppizil.raven.common.ui.theme.RavenTheme

@Composable
fun App() {
    RavenTheme {
        val dummyDocuments = listOf(
            com.ppizil.raven.common.db.Document("1", "Doc 1: Home", "Welcome to Raven.", false, 0),
            com.ppizil.raven.common.db.Document("2", "Doc 2: Ideas", "Here are some ideas.", false, 0),
            com.ppizil.raven.common.db.Document("3", "Doc 3: Meeting Notes", "Notes from the meeting.", false, 0)
        )
        SlidingPanelLayout(
            documents = dummyDocuments,
            modifier = Modifier.fillMaxSize()
        )
    }
}

expect fun getPlatformName(): String