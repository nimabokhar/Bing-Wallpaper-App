plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Optional stable signing key, supplied by CI from repository secrets. Without it
// the APK is signed with a throwaway debug key, so a new build can only be
// installed after uninstalling the previous one.
val signingStoreFile = System.getenv("SIGNING_STORE_FILE")?.let { file(it) }?.takeIf { it.exists() }

android {
    namespace = "com.nimabokhar.bingwallpaper"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.nimabokhar.bingwallpaper"
        minSdk = 24
        targetSdk = 35
        val run = System.getenv("GITHUB_RUN_NUMBER")?.toIntOrNull() ?: 1
        versionCode = run
        versionName = "1.0.$run"
    }

    signingConfigs {
        if (signingStoreFile != null) {
            create("stable") {
                storeFile = signingStoreFile
                storePassword = System.getenv("SIGNING_STORE_PASSWORD")
                keyAlias = System.getenv("SIGNING_KEY_ALIAS")
                keyPassword = System.getenv("SIGNING_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("stable") ?: signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
}
