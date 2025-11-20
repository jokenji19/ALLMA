# Integrazione Android ALLMA

## 1. Architettura Android

### 1.1 Struttura Progetto Android
```
app/
├── src/
│   ├── main/
│   │   ├── java/com/allma/
│   │   │   ├── activities/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   └── ChatActivity.kt
│   │   │   ├── services/
│   │   │   │   ├── ALLMAService.kt
│   │   │   │   ├── LearningService.kt
│   │   │   │   └── NotificationService.kt
│   │   │   ├── viewmodels/
│   │   │   │   ├── ChatViewModel.kt
│   │   │   │   ├── LearningViewModel.kt
│   │   │   │   └── MainViewModel.kt
│   │   │   ├── repository/
│   │   │   │   ├── ALLMARepository.kt
│   │   │   │   ├── LearningRepository.kt
│   │   │   │   └── DatabaseRepository.kt
│   │   │   └── utils/
│   │   │       ├── ALLMAWrapper.kt
│   │   │       └── SecurityManager.kt
│   │   └── res/
│   │       ├── layout/
│   │       ├── values/
│   │       └── drawable/
│   └── test/
└── build.gradle
```

## 2. Componenti Principali

### 2.1 ALLMAService
```kotlin
class ALLMAService : Service() {
    private val allma = IntegratedALLMA()
    private val learningManager = LearningManager()
    private val binder = ALLMABinder()
    
    inner class ALLMABinder : Binder() {
        fun getService(): ALLMAService = this@ALLMAService
    }
    
    override fun onBind(intent: Intent): IBinder = binder
    
    fun processInput(text: String, context: Map<String, Any>? = null): ProcessingResult {
        return allma.processInput(text, context)
    }
    
    fun handleUnknownConcept(concept: String, explanation: String) {
        learningManager.learnNewConcept(concept, explanation)
    }
}
```

### 2.2 LearningService
```kotlin
class LearningService : Service() {
    private val learningSystem = LearningSystem()
    private val curiositySystem = CuriositySystem()
    private val binder = LearningBinder()
    
    inner class LearningBinder : Binder() {
        fun getService(): LearningService = this@LearningService
    }
    
    fun identifyUnknownConcepts(text: String): List<String> {
        return curiositySystem.identifyUnknown(text)
    }
    
    fun generateQuestions(concepts: List<String>): List<String> {
        return learningSystem.generateQuestions(concepts)
    }
    
    fun learnFromFeedback(concept: String, explanation: String): Boolean {
        return learningSystem.learnFromFeedback(concept, explanation)
    }
}
```

### 2.3 ViewModels
```kotlin
class ChatViewModel @Inject constructor(
    private val allmaRepository: ALLMARepository,
    private val learningRepository: LearningRepository
) : ViewModel() {
    private val _chatState = MutableLiveData<ChatState>()
    val chatState: LiveData<ChatState> = _chatState
    
    private val _learningState = MutableLiveData<LearningState>()
    val learningState: LiveData<LearningState> = _learningState
    
    fun processMessage(message: String) {
        viewModelScope.launch {
            val result = allmaRepository.processInput(message)
            
            if (result.unknownConcepts.isNotEmpty()) {
                val questions = learningRepository.generateQuestions(
                    result.unknownConcepts
                )
                _learningState.value = LearningState.Questions(questions)
            }
            
            _chatState.value = ChatState.Response(result.response)
        }
    }
    
    fun handleExplanation(concept: String, explanation: String) {
        viewModelScope.launch {
            learningRepository.learnFromFeedback(concept, explanation)
            _learningState.value = LearningState.Learned(concept)
        }
    }
}
```

### 2.4 Repositories
```kotlin
class ALLMARepository @Inject constructor(
    private val allmaService: ALLMAService,
    private val database: AppDatabase
) {
    suspend fun processInput(
        text: String,
        context: Map<String, Any>? = null
    ): ProcessingResult = withContext(Dispatchers.IO) {
        val result = allmaService.processInput(text, context)
        database.messageDao().insert(
            Message(text = text, timestamp = System.currentTimeMillis())
        )
        result
    }
}

class LearningRepository @Inject constructor(
    private val learningService: LearningService,
    private val database: AppDatabase
) {
    suspend fun learnFromFeedback(
        concept: String,
        explanation: String
    ): Boolean = withContext(Dispatchers.IO) {
        val success = learningService.learnFromFeedback(concept, explanation)
        if (success) {
            database.conceptDao().insert(
                Concept(name = concept, explanation = explanation)
            )
        }
        success
    }
}
```

## 3. UI/UX

### 3.1 Layout Chat
```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/chatRecyclerView"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        app:layout_constraintBottom_toTopOf="@id/inputContainer"
        app:layout_constraintTop_toTopOf="parent" />

    <LinearLayout
        android:id="@+id/inputContainer"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:padding="8dp"
        app:layout_constraintBottom_toBottomOf="parent">

        <EditText
            android:id="@+id/messageInput"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:hint="@string/message_hint" />

        <ImageButton
            android:id="@+id/sendButton"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:src="@drawable/ic_send" />
    </LinearLayout>

</androidx.constraintlayout.widget.ConstraintLayout>
```

### 3.2 Gestione Stati
```kotlin
sealed class ChatState {
    data class Response(val message: String) : ChatState()
    data class Error(val message: String) : ChatState()
    object Loading : ChatState()
}

sealed class LearningState {
    data class Questions(val questions: List<String>) : LearningState()
    data class Learned(val concept: String) : LearningState()
    data class Error(val message: String) : LearningState()
}
```

## 4. Persistenza Dati

### 4.1 Room Database
```kotlin
@Entity(tableName = "messages")
data class Message(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val text: String,
    val timestamp: Long,
    val emotional_context: String? = null,
    val learning_context: String? = null
)

@Entity(tableName = "concepts")
data class Concept(
    @PrimaryKey val name: String,
    val explanation: String,
    val learned_at: Long = System.currentTimeMillis(),
    val confidence: Float = 1.0f
)

@Database(
    entities = [Message::class, Concept::class],
    version = 1
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun messageDao(): MessageDao
    abstract fun conceptDao(): ConceptDao
}
```

## 5. Sicurezza

### 5.1 Crittografia
```kotlin
object SecurityManager {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val encryptedPreferences = EncryptedSharedPreferences.create(
        context,
        "secret_shared_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    fun storeSecurely(key: String, value: String) {
        encryptedPreferences.edit().putString(key, value).apply()
    }
    
    fun retrieveSecurely(key: String): String? {
        return encryptedPreferences.getString(key, null)
    }
}
```

## 6. Testing

### 6.1 Unit Tests
```kotlin
@RunWith(AndroidJUnit4::class)
class ALLMAServiceTest {
    private lateinit var service: ALLMAService
    
    @Before
    fun setup() {
        service = ALLMAService()
    }
    
    @Test
    fun testProcessInput() {
        val result = service.processInput("Test message")
        assertNotNull(result)
        assertTrue(result.confidence > 0.5)
    }
    
    @Test
    fun testLearning() {
        val concept = "test_concept"
        val explanation = "Test explanation"
        val success = service.handleUnknownConcept(concept, explanation)
        assertTrue(success)
    }
}
```

### 6.2 Integration Tests
```kotlin
@RunWith(AndroidJUnit4::class)
class ChatViewModelTest {
    @get:Rule
    val instantExecutorRule = InstantTaskExecutorRule()
    
    private lateinit var viewModel: ChatViewModel
    private lateinit var repository: ALLMARepository
    
    @Before
    fun setup() {
        repository = mock()
        viewModel = ChatViewModel(repository)
    }
    
    @Test
    fun testMessageProcessing() = runBlockingTest {
        val message = "Test message"
        val result = ProcessingResult(
            response = "Test response",
            confidence = 0.8f
        )
        
        whenever(repository.processInput(message))
            .thenReturn(result)
            
        viewModel.processMessage(message)
        
        verify(repository).processInput(message)
        assertEquals(
            ChatState.Response(result.response),
            viewModel.chatState.value
        )
    }
}
```

## 7. Performance

### 7.1 Ottimizzazioni
```kotlin
class PerformanceOptimizer {
    private val cache = LruCache<String, ProcessingResult>(100)
    
    fun optimizeProcessing(
        text: String,
        process: (String) -> ProcessingResult
    ): ProcessingResult {
        return cache.get(text) ?: process(text).also {
            cache.put(text, it)
        }
    }
    
    fun clearCache() {
        cache.evictAll()
    }
}
```

### 7.2 Monitoraggio
```kotlin
class PerformanceMonitor {
    private val metrics = mutableMapOf<String, List<Long>>()
    
    fun trackOperation(name: String, block: () -> Unit) {
        val start = System.nanoTime()
        block()
        val duration = System.nanoTime() - start
        
        metrics[name] = (metrics[name] ?: emptyList()) + duration
    }
    
    fun getAverageTime(name: String): Double {
        return metrics[name]?.average() ?: 0.0
    }
}
```

## 8. Dipendenze Gradle
```gradle
dependencies {
    // Core ALLMA
    implementation 'com.allma:core:1.2.3'
    implementation 'com.allma:emotional:1.2.3'
    implementation 'com.allma:memory:1.2.3'
    implementation 'com.allma:cognitive:1.2.3'
    
    // Machine Learning
    implementation 'org.tensorflow:tensorflow-lite:2.9.0'
    implementation 'org.tensorflow:tensorflow-lite-support:0.4.2'
    implementation 'org.tensorflow:tensorflow-lite-metadata:0.4.2'
    
    // Utils
    implementation 'androidx.lifecycle:lifecycle-viewmodel-ktx:2.6.1'
    implementation 'androidx.lifecycle:lifecycle-livedata-ktx:2.6.1'
    implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.6.4'
    
    // Testing
    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.1.5'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
}
```

## 9. Configurazione AndroidManifest
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.allma.android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" 
        android:maxSdkVersion="28"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />

    <application
        android:name=".ALLMAApplication"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme">
        
        <service
            android:name=".services.ALLMAService"
            android:exported="false"/>
            
        <provider
            android:name=".data.ALLMAContentProvider"
            android:authorities="${applicationId}.provider"
            android:exported="false"/>
    </application>
</manifest>
```

## 10. Application Class
```kotlin
class ALLMAApplication : Application() {
    lateinit var allmaComponent: ALLMAComponent
    
    override fun onCreate() {
        super.onCreate()
        initializeALLMA()
    }
    
    private fun initializeALLMA() {
        allmaComponent = DaggerALLMAComponent.builder()
            .applicationModule(ApplicationModule(this))
            .allmaModule(ALLMAModule())
            .build()
    }
}
```

## 11. Dependency Injection
```kotlin
@Module
class ALLMAModule {
    @Provides
    @Singleton
    fun provideEmotionalSystem(): EmotionalSystem {
        return EmotionalSystem(
            modelConfig = EmotionalModelConfig(
                modelPath = "models/emotional_model.tflite",
                labelPath = "models/emotional_labels.txt"
            )
        )
    }
    
    @Provides
    @Singleton
    fun provideMemorySystem(
        @ApplicationContext context: Context
    ): MemorySystem {
        return MemorySystem(
            context = context,
            config = MemoryConfig(
                databaseName = "allma_memory.db",
                maxSize = 1024 * 1024 * 50 // 50MB
            )
        )
    }
}
```

## 12. Componenti UI

### 12.1 Activity Principale
```kotlin
class MainActivity : AppCompatActivity() {
    private val viewModel: ALLMAViewModel by viewModels()
    private lateinit var binding: ActivityMainBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupUI()
        observeViewModel()
    }
    
    private fun setupUI() {
        binding.inputField.apply {
            setOnEditorActionListener { _, actionId, _ ->
                if (actionId == EditorInfo.IME_ACTION_SEND) {
                    processInput()
                    true
                } else false
            }
        }
    }
    
    private fun observeViewModel() {
        viewModel.responses.observe(this) { response ->
            updateUI(response)
        }
        
        viewModel.emotionalState.observe(this) { emotion ->
            updateEmotionalUI(emotion)
        }
    }
}
```

### 12.2 ViewModel
```kotlin
@HiltViewModel
class ALLMAViewModel @Inject constructor(
    private val allmaRepository: ALLMARepository,
    private val emotionalSystem: EmotionalSystem,
    private val memorySystem: MemorySystem
) : ViewModel() {
    
    private val _responses = MutableLiveData<List<Response>>()
    val responses: LiveData<List<Response>> = _responses
    
    private val _emotionalState = MutableLiveData<Emotion>()
    val emotionalState: LiveData<Emotion> = _emotionalState
    
    fun processInput(input: String) = viewModelScope.launch {
        val result = allmaRepository.processInput(input)
        updateResponses(result)
        updateEmotionalState(result.emotion)
    }
    
    private fun updateResponses(result: ProcessingResult) {
        val currentResponses = _responses.value.orEmpty().toMutableList()
        currentResponses.add(result.response)
        _responses.value = currentResponses
    }
}
```

## 13. Gestione Dati

### 13.1 Room Database
```kotlin
@Database(
    entities = [
        Memory::class,
        Emotion::class,
        Concept::class
    ],
    version = 1
)
abstract class ALLMADatabase : RoomDatabase() {
    abstract fun memoryDao(): MemoryDao
    abstract fun emotionDao(): EmotionDao
    abstract fun conceptDao(): ConceptDao
    
    companion object {
        private const val DATABASE_NAME = "allma_db"
        
        fun create(context: Context): ALLMADatabase {
            return Room.databaseBuilder(
                context,
                ALLMADatabase::class.java,
                DATABASE_NAME
            ).build()
        }
    }
}
```

### 13.2 Repository Pattern
```kotlin
class ALLMARepository @Inject constructor(
    private val memoryDao: MemoryDao,
    private val emotionDao: EmotionDao,
    private val conceptDao: ConceptDao,
    private val allmaService: ALLMAService
) {
    suspend fun processInput(input: String): ProcessingResult {
        val emotion = emotionDao.getLatestEmotion()
        val memories = memoryDao.getRelevantMemories(input)
        
        return allmaService.process(
            input = input,
            emotion = emotion,
            memories = memories
        ).also { result ->
            saveProcessingResult(result)
        }
    }
    
    private suspend fun saveProcessingResult(result: ProcessingResult) {
        emotionDao.insert(result.emotion)
        memoryDao.insert(result.memory)
        conceptDao.insertAll(result.concepts)
    }
}
```

## 14. Background Processing

### 14.1 Service Implementation
```kotlin
class ALLMAService : LifecycleService() {
    @Inject lateinit var allmaProcessor: ALLMAProcessor
    @Inject lateinit var notificationManager: NotificationManager
    
    private val processingScope = CoroutineScope(
        Dispatchers.Default + SupervisorJob()
    )
    
    override fun onCreate() {
        super.onCreate()
        startForeground()
    }
    
    fun processInBackground(input: String) {
        processingScope.launch {
            val result = allmaProcessor.process(input)
            handleResult(result)
        }
    }
    
    private fun handleResult(result: ProcessingResult) {
        when (result) {
            is Success -> notifySuccess(result)
            is Error -> notifyError(result)
        }
    }
}
```

### 14.2 WorkManager Integration
```kotlin
class ALLMAWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    override suspend fun doWork(): Result {
        val input = inputData.getString(KEY_INPUT)
            ?: return Result.failure()
            
        return try {
            val result = processInput(input)
            Result.success(workDataOf(KEY_RESULT to result))
        } catch (e: Exception) {
            Result.failure()
        }
    }
    
    companion object {
        private const val KEY_INPUT = "key_input"
        private const val KEY_RESULT = "key_result"
        
        fun createRequest(input: String): OneTimeWorkRequest {
            return OneTimeWorkRequestBuilder<ALLMAWorker>()
                .setInputData(workDataOf(KEY_INPUT to input))
                .setConstraints(Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
                )
                .build()
        }
    }
}
```

## 15. Ottimizzazione Performance

### 15.1 Memory Management
```kotlin
object MemoryOptimizer {
    private const val MAX_CACHE_SIZE = 50 * 1024 * 1024 // 50MB
    
    fun initializeCache(context: Context) {
        val cacheDir = context.cacheDir
        DiskLruCache.open(
            cacheDir,
            1,
            1,
            MAX_CACHE_SIZE.toLong()
        )
    }
    
    fun clearOldCache(context: Context) {
        val cacheDir = context.cacheDir
        val maxAge = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000) // 1 week
        
        cacheDir.listFiles()?.forEach { file ->
            if (file.lastModified() < maxAge) {
                file.delete()
            }
        }
    }
}
```

### 15.2 Battery Optimization
```kotlin
class BatteryOptimizer @Inject constructor(
    private val context: Context
) {
    private val powerManager = context.getSystemService<PowerManager>()
    
    fun optimizeProcessing(block: suspend () -> Unit) {
        val wakeLock = powerManager?.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "ALLMA:ProcessingLock"
        )
        
        try {
            wakeLock?.acquire(10 * 60 * 1000L) // 10 minutes
            runBlocking { block() }
        } finally {
            wakeLock?.release()
        }
    }
}
```

## 16. Testing

### 16.1 Unit Tests
```kotlin
@RunWith(AndroidJUnit4::class)
class ALLMAIntegrationTest {
    private lateinit var allmaProcessor: ALLMAProcessor
    private lateinit var db: ALLMADatabase
    
    @Before
    fun setup() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(
            context,
            ALLMADatabase::class.java
        ).build()
        
        allmaProcessor = ALLMAProcessor(
            emotionalSystem = MockEmotionalSystem(),
            memorySystem = MockMemorySystem(),
            database = db
        )
    }
    
    @Test
    fun testProcessing() = runBlocking {
        val input = "Test input"
        val result = allmaProcessor.process(input)
        
        assertNotNull(result)
        assertEquals(ProcessingStatus.SUCCESS, result.status)
    }
}
```

### 16.2 UI Tests
```kotlin
@RunWith(AndroidJUnit4::class)
class MainActivityTest {
    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)
    
    @Test
    fun testUserInput() {
        onView(withId(R.id.input_field))
            .perform(typeText("Test input"), closeSoftKeyboard())
        
        onView(withId(R.id.send_button))
            .perform(click())
        
        onView(withId(R.id.response_text))
            .check(matches(isDisplayed()))
            .check(matches(withText(containsString("response"))))
    }
}
```

## 17. Sicurezza

### 17.1 Encryption
```kotlin
object SecurityManager {
    private const val ALGORITHM = "AES/GCM/NoPadding"
    private const val KEY_SIZE = 256
    
    fun encrypt(data: String): String {
        val cipher = Cipher.getInstance(ALGORITHM)
        val key = generateKey()
        cipher.init(Cipher.ENCRYPT_MODE, key)
        
        val encrypted = cipher.doFinal(data.toByteArray())
        return Base64.encodeToString(encrypted, Base64.DEFAULT)
    }
    
    private fun generateKey(): SecretKey {
        val keyGenerator = KeyGenerator.getInstance("AES")
        keyGenerator.init(KEY_SIZE)
        return keyGenerator.generateKey()
    }
}
```

### 17.2 Data Protection
```kotlin
class DataProtectionManager @Inject constructor(
    private val context: Context
) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val encryptedPreferences = EncryptedSharedPreferences.create(
        context,
        "secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    fun secureStore(key: String, value: String) {
        encryptedPreferences.edit().putString(key, value).apply()
    }
    
    fun secureRetrieve(key: String): String? {
        return encryptedPreferences.getString(key, null)
    }
}
```

## 18. Monitoraggio e Analytics

### 18.1 Performance Monitoring
```kotlin
class PerformanceMonitor @Inject constructor(
    private val context: Context
) {
    private val metrics = mutableMapOf<String, Long>()
    
    fun startOperation(name: String) {
        metrics[name] = System.nanoTime()
    }
    
    fun endOperation(name: String) {
        val startTime = metrics[name] ?: return
        val duration = System.nanoTime() - startTime
        
        logMetric(name, duration)
    }
    
    private fun logMetric(name: String, duration: Long) {
        FirebaseAnalytics.getInstance(context).logEvent(
            "performance_metric",
            bundleOf(
                "name" to name,
                "duration_ms" to TimeUnit.NANOSECONDS.toMillis(duration)
            )
        )
    }
}
```

### 18.2 Error Tracking
```kotlin
class ErrorTracker @Inject constructor(
    private val context: Context
) {
    fun trackError(
        error: Throwable,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) {
        val errorData = bundleOf(
            "error_type" to error.javaClass.simpleName,
            "error_message" to error.message,
            "severity" to severity.name
        )
        
        FirebaseCrashlytics.getInstance().apply {
            setCustomKey("severity", severity.name)
            recordException(error)
        }
        
        FirebaseAnalytics.getInstance(context)
            .logEvent("error_occurred", errorData)
    }
}
```
