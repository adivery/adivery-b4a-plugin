# Adivery B4A Plugin

A [B4A (Basic4android)](https://www.b4x.com/b4a.html) library that wraps the
[Adivery](https://adivery.com) Android SDK: interstitial, rewarded, App Open,
Offer Wall and banner ads, used from B4A code.

Repo layout:

```
b4a-plugin/src/com/adivery/b4a/  → the Java wrapper, compiled into Adivery.jar + Adivery.xml by B4A's LibraryCompiler
sample/                          → a B4A sample project (ui_example.b4a) that shows every format
build.bat                        → runs LibraryCompiler (Windows only)
.claude/skills/                  → Claude Code skills to sync with a new SDK version and to publish a release
```

## Installing the library in your B4A project

The full guide, in Persian, is at [docs.adivery.com/b4a](https://docs.adivery.com/b4a).
In short:

1. Download [`adivery-b4a.zip`](https://github.com/adivery/adivery-b4a-plugin/releases/latest/download/adivery-b4a.zip)
   from the latest release. Extract `Adivery.jar`, `Adivery.xml` and `Adivery.aar` (the
   Adivery SDK) into your B4A Additional Libraries folder, and tick **Adivery** in the
   Libraries tab.
2. B4A doesn't resolve the SDK's own dependencies. Download these jars from Maven Central
   into the same folder (the docs link each one), and add them to your project:

   ```vb
   #AdditionalJar: kotlin-stdlib-2.1.10
   #AdditionalJar: okhttp-4.12.0
   #AdditionalJar: okio-jvm-3.6.0
   #AdditionalJar: sentry-8.7.0
   #AdditionalJar: kotlinx-coroutines-core-jvm-1.10.1
   #AdditionalJar: kotlinx-coroutines-android-1.10.1
   ```

   The two `kotlinx-coroutines` jars are new in v4.10.0-alpha.1. Without them, ads fail
   to load.
3. Declare the SDK's ad activity in the Manifest Editor:

   ```xml
   AddApplicationText(
   <activity
       android:name="com.adivery.sdk.networks.adivery.AdActivity"
       android:configChanges="keyboard|keyboardHidden|orientation|screenLayout|uiMode|screenSize|smallestScreenSize"
       android:exported="false" />)
   ```
4. Let the SDK read the advertising ID. B4A doesn't merge the SDK's own manifest, and on
   Android 13+ Google Play services returns an all-zero ID to apps that don't declare
   `AD_ID`, so the server has nothing to target and can return no ads (the offer wall
   needs it). Add to the Manifest Editor:

   ```xml
   AddPermission(com.google.android.gms.permission.AD_ID)
   AddPermission(android.permission.ACCESS_NETWORK_STATE)
   AddManifestText(
   <queries>
       <package android:name="com.android.vending" />
       <package android:name="com.farsitel.bazaar" />
       <package android:name="ir.mservices.market" />
       <package android:name="com.huawei.hwid" />
       <package android:name="com.huawei.hms" />
       <package android:name="com.huawei.hwid.tv" />
       <intent><action android:name="android.intent.action.VIEW" /><data android:scheme="market" /></intent>
       <intent><action android:name="android.intent.action.VIEW" /><data android:scheme="bazaar" /></intent>
       <intent><action android:name="android.intent.action.VIEW" /><data android:scheme="myket" /></intent>
       <intent><action android:name="android.intent.action.VIEW" /><data android:scheme="http" /></intent>
       <intent><action android:name="android.intent.action.VIEW" /><data android:scheme="https" /></intent>
   </queries>)
   ```

Basic usage:

```vb
Sub Globals
	Dim Adivery As Adivery
End Sub

Sub Activity_Create(FirstTime As Boolean)
	Adivery.Initialize("YOUR_APP_ID")
	Adivery.PrepareInterstitialAd("YOUR_PLACEMENT_ID")
End Sub

Sub On_Interstitial_Ad_Loaded(placement As String)
	Adivery.Show(placement)
End Sub

Sub On_Error(placement As String, error As String)
	Log(error)
End Sub
```

## API

`Adivery`:

| Member | What it does |
|---|---|
| `Initialize(AppId As String)` | Configures the SDK. Call it first, from your main activity. |
| `SetLoggingEnabled(Enabled As Boolean)` | Turns the SDK's logging on or off. |
| `SetUserId(UserId As String)` | Identifies the user for [server-side reward verification](https://docs.adivery.com/server) (sent as `uid`). |
| `IsLoaded(PlacementId As String) As Boolean` | Whether an ad is ready to show for that placement. |
| `AddListener(Name As String)` / `RemoveListener(Name As String)` | Also raise the calling activity's events to Subs named `Name_On_...`. |

| Format | Load | Show | Events (`placement As String` first) |
|---|---|---|---|
| Interstitial | `PrepareInterstitialAd` | `Show` | `On_Interstitial_Ad_Loaded`, `_Shown`, `_Clicked`, `_Closed` |
| Rewarded | `PrepareRewardedAd` | `Show` | `On_Rewarded_Ad_Loaded`, `_Shown`, `_Clicked`, and `On_Rewarded_Ad_Closed(placement, reward As Boolean)` |
| App Open | `PrepareAppOpenAd` | `ShowAppOpen` | `On_App_Open_Ad_Loaded`, `_Shown`, `_Clicked`, `_Closed` |
| Offer Wall | `PrepareOfferWallAd` | `Show` | `On_Offer_Wall_Ad_Loaded`, `_Shown`, `_Clicked`, `_Closed`, and `On_Offer_Wall_Mission_Rewarded(placement, currency As String, amount As Int)` |

Errors for every format arrive in `On_Error(placement As String, error As String)`.

- **Where events arrive.** `Initialize` raises events to `On_...` Subs in the activity that
  called it. `AddListener(Name)` adds `Name_On_...` Subs in the calling activity. Either way,
  an activity's Subs only run while it's in front.
- **Reloading.** Interstitial, rewarded and App Open ads load the next ad by themselves after
  one closes.
- **The Offer Wall** needs v4.10.0-alpha.1 or later.
  - Don't preload it: call `PrepareOfferWallAd` when the user opens it, and `Show` it from
    `On_Offer_Wall_Ad_Loaded`.
  - It isn't loaded again after it closes, so prepare it each time.
  - `On_Offer_Wall_Mission_Rewarded` can run several times per showing.

`AdiveryBannerAd` is a view. `Initialize2(EventName, PlacementId, Size)` loads it, with
`Size` one of `BANNER`, `LARGE_BANNER`, `MEDIUM_RECTANGLE` or `SMART_BANNER`. Add it to your
layout with `Activity.AddView`. It raises `<EventName>_Ad_Loaded`, `<EventName>_Ad_Clicked`
and `<EventName>_Ad_Error(error As String)`:

```vb
Sub Globals
	Dim Banner As AdiveryBannerAd
End Sub

Sub ShowBanner
	Banner.Initialize2("MyBanner", "YOUR_PLACEMENT_ID", Banner.BANNER)
	Activity.AddView(Banner, (100%x - 320dip) / 2, 100%y - 50dip, 320dip, 50dip)
End Sub

Sub MyBanner_Ad_Loaded
	Log("banner loaded")
End Sub

Sub MyBanner_Ad_Error(error As String)
	Log(error)
End Sub
```

## Building the library

B4A's LibraryCompiler only runs on Windows:

1. Extract `classes.jar` from the Adivery SDK's `sdk-X.Y.Z.aar` (from
   [Maven Central](https://repo1.maven.org/maven2/com/adivery/sdk/)) into `b4a-plugin/libs/`.
   `*.jar` is gitignored.
2. Run `build.bat`. It writes `Adivery.jar` and `Adivery.xml` to B4A's Additional Libraries
   folder.
3. Copy `sdk-X.Y.Z.aar` next to them as `Adivery.aar` to run the sample.

## Maintaining

Plugin versions track Adivery SDK versions: SDK `X.Y.Z` is release `vX.Y.Z`. The release zip
holds `adivery-b4a/Adivery.{jar,xml,aar}`. Two Claude Code skills cover the workflow:

- `new-plugin-version` syncs the wrapper, sample and docs with a new SDK version.
  - It checks the Java against the published SDK and against the API customers already
    have.
  - It hands the Windows rebuild to you, then verifies the jar you send back.
- `release-b4a-plugin` packages the zip and publishes the GitHub release.

Their helper scripts also run on their own. For example, `bridge.py check` checks the
wrapper, the sample and this README against an SDK AAR (see
`.claude/skills/new-plugin-version/SKILL.md`).
