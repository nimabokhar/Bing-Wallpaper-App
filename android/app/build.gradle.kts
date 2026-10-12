plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Optional stable signing key, supplied by CI from repository secrets. Without it
// the APK is signed with a throwaway debug key, so a new build can only be
// installed after uninstalling the previous one.
val signingStoreFile = System.getenv("SIGNING_STORE_FILE")?.let { file(it) }?.takeIf { it.exists() }

// The version is shared by every platform and lives in VERSION at the repository
// root, as MAJOR.MINOR.PATCH with an optional -alpha.N, -beta.N or -rc.N suffix.
val appVersion = rootDir.resolve("../VERSION").readText().trim()

// Turns the version into an always-increasing versionCode so Android installs
// upgrades in order: 0.1.0-alpha.1 -> 100101, 0.1.0-beta.2 -> 100202,
// 0.1.0 -> 100900, 1.2.3 -> 10203900.
fun versionCodeOf(version: String): Int {
    val match = Regex("""(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?""").matchEntire(version)
        ?: error("VERSION must look like 1.2.3 or 1.2.3-alpha.4, got \"$version\"")
    val (major, minor, patch, stage, number) = match.destructured
    require(minor.toInt() < 100 && patch.toInt() < 100 && (number.toIntOrNull() ?: 0) < 100) {
        "Minor, patch and pre-release numbers must be below 100 to fit the versionCode, got $version"
    }
    val stageCode = when (stage) {
        "alpha" -> 100 + number.toInt()
        "beta" -> 200 + number.toInt()
        "rc" -> 300 + number.toInt()
        else -> 900
    }
    return major.toInt() * 10_000_000 + minor.toInt() * 100_000 + patch.toInt() * 1_000 + stageCode
}

// CI builds of main between releases add the run number as build metadata
// (0.1.0-alpha.1+build.42) so the app shows exactly which build is installed.
val buildNumber = System.getenv("BUILD_NUMBER")?.takeIf { it.isNotBlank() }

android {
    namespace = "com.nimabokhar.bingwallpaper"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.nimabokhar.bingwallpaper"
        minSdk = 24
        targetSdk = 35
        versionCode = versionCodeOf(appVersion)
        versionName = if (buildNumber != null) "$appVersion+build.$buildNumber" else appVersion
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
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

    buildFeatures {
        buildConfig = true
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
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.work:work-runtime-ktx:2.9.1")

    androidTestImplementation("androidx.test:core-ktx:1.6.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
