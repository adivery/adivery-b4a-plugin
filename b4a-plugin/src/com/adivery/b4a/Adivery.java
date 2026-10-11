package com.adivery.b4a;

import java.util.HashMap;

import com.adivery.sdk.AdiveryListener;

import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;

@ShortName("Adivery")
@Version(4.91f)
@Permissions(values = { "android.permission.INTERNET" })
@DependsOn(values = { "Adivery.aar" })
@Events(values = {
		"On_Error (placement As String , error As String )",
		"On_Interstitial_Ad_Clicked( placement As String )",
		"On_Interstitial_Ad_Closed ( placement As String )",
		"On_Interstitial_Ad_Loaded ( placement As String )",
		"On_Interstitial_Ad_Shown ( placement As String )",
		"On_Rewarded_Ad_Clicked ( placement As String )",
		"On_Rewarded_Ad_Closed ( placement As String , reward As Boolean )",
		"On_Rewarded_Ad_Loaded ( placement As String )",
		"On_Rewarded_Ad_Shown (placement As String )",
		"On_App_Open_Ad_Clicked ( placement As String )",
		"On_App_Open_Ad_Closed ( placement As String )",
		"On_App_Open_Ad_Loaded ( placement As String )",
		"On_App_Open_Ad_Shown ( placement As String )",
		"On_Offer_Wall_Ad_Clicked ( placement As String )",
		"On_Offer_Wall_Ad_Closed ( placement As String )",
		"On_Offer_Wall_Ad_Loaded ( placement As String )",
		"On_Offer_Wall_Ad_Shown ( placement As String )",
		"On_Offer_Wall_Mission_Rewarded ( placement As String , currency As String , amount As Int )"
})
@ActivityObject
public class Adivery {

	// Listeners by event-name prefix + activity: each raises events only while its activity is in front.
	static HashMap<String, AdiveryListener> listeners = new HashMap<String, AdiveryListener>();
	static String currentActivity = "main";
	static boolean lifecycleRegistered = false;
	static ActivityChangeListener.OnActivityChangedListener listener = new ActivityChangeListener.OnActivityChangedListener() {
		@Override
		public void onActivityChanged(String name) {
			currentActivity = name;
		}
	};

	public static void Initialize(BA ba, String appId) {
		com.adivery.sdk.Adivery.configure(BA.applicationContext, appId);
		if (!lifecycleRegistered) {
			BA.applicationContext.registerActivityLifecycleCallbacks(new ActivityChangeListener(listener));
			lifecycleRegistered = true;
		}
		addAdiveryListener(ba, "");
	}

	/**
	 * Also raises this activity's events to Subs named name_On_..., e.g. name_On_Interstitial_Ad_Loaded.
	 */
	public static void AddListener(BA ba, String name) {
		addAdiveryListener(ba, name + "_");
	}

	public static void RemoveListener(BA ba, String name) {
		AdiveryListener adiveryListener = listeners.remove(name + "_" + currentActivity);
		if (adiveryListener != null) {
			com.adivery.sdk.Adivery.removeGlobalListener(adiveryListener);
		}
	}

	public static void SetLoggingEnabled(BA ba, boolean enabled) {
		com.adivery.sdk.Adivery.setLoggingEnabled(enabled);
	}

	public static void SetUserId(BA ba, String userId) {
		com.adivery.sdk.Adivery.setUserId(userId);
	}

	public static void PrepareInterstitialAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareInterstitialAd(BA.applicationContext, placementId);
	}

	public static void PrepareRewardedAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareRewardedAd(BA.applicationContext, placementId);
	}

	public static void PrepareAppOpenAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareAppOpenAd(ba.activity, placementId);
	}

	/**
	 * Loads an Offer Wall. Call it each time the user opens the Offer Wall and Show it from
	 * On_Offer_Wall_Ad_Loaded: it isn't loaded again after it closes.
	 */
	public static void PrepareOfferWallAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareOfferWallAd(ba.activity, placementId);
	}

	public static void Show(BA ba, String placementId) {
		com.adivery.sdk.Adivery.showAd(placementId);
	}

	public static void ShowAppOpen(BA ba, String placementId) {
		com.adivery.sdk.Adivery.showAppOpenAd(ba.activity, placementId);
	}

	public static boolean IsLoaded(BA ba, String placementId) {
		return com.adivery.sdk.Adivery.isLoaded(placementId);
	}

	private static void addAdiveryListener(BA ba, String name) {
		String key = name + currentActivity;
		if (!listeners.containsKey(key)) {
			AdiveryListener adiveryListener = new B4aAdiveryListener(ba, name, currentActivity);
			com.adivery.sdk.Adivery.addGlobalListener(adiveryListener);
			listeners.put(key, adiveryListener);
		}
	}

	public static void raiseEvent(BA ba, String name, Object... params) {
		if (ba.subExists(name)) {
			ba.raiseEventFromDifferentThread(Adivery.class, ba, 0, name, false, params);
		}
	}

	static class B4aAdiveryListener extends AdiveryListener {
		final BA ba;
		final String name;
		final String activity;

		B4aAdiveryListener(BA ba, String name, String activity) {
			this.ba = ba;
			this.name = name;
			this.activity = activity;
		}

		void raiseEvent(BA ba, String event, Object... params) {
			if (currentActivity.equals(activity)) {
				Adivery.raiseEvent(ba, name.toLowerCase(BA.cul) + event, params);
			}
		}

		@Override
		public void log(String placementId, String message) {
			raiseEvent(ba, "on_error", placementId, message);
		}

		@Override
		public void onInterstitialAdClicked(String placementId) {
			raiseEvent(ba, "on_interstitial_ad_clicked", placementId);
		}

		@Override
		public void onInterstitialAdClosed(String placementId) {
			raiseEvent(ba, "on_interstitial_ad_closed", placementId);
		}

		@Override
		public void onInterstitialAdLoaded(String placementId) {
			raiseEvent(ba, "on_interstitial_ad_loaded", placementId);
		}

		@Override
		public void onInterstitialAdShown(String placementId) {
			raiseEvent(ba, "on_interstitial_ad_shown", placementId);
		}

		@Override
		public void onRewardedAdClicked(String placementId) {
			raiseEvent(ba, "on_rewarded_ad_clicked", placementId);
		}

		@Override
		public void onRewardedAdClosed(String placementId, boolean isRewarded) {
			raiseEvent(ba, "on_rewarded_ad_closed", placementId, isRewarded);
		}

		@Override
		public void onRewardedAdLoaded(String placementId) {
			raiseEvent(ba, "on_rewarded_ad_loaded", placementId);
		}

		@Override
		public void onRewardedAdShown(String placementId) {
			raiseEvent(ba, "on_rewarded_ad_shown", placementId);
		}

		@Override
		public void onAppOpenAdClicked(String placementId) {
			raiseEvent(ba, "on_app_open_ad_clicked", placementId);
		}

		@Override
		public void onAppOpenAdClosed(String placementId) {
			raiseEvent(ba, "on_app_open_ad_closed", placementId);
		}

		@Override
		public void onAppOpenAdLoaded(String placementId) {
			raiseEvent(ba, "on_app_open_ad_loaded", placementId);
		}

		@Override
		public void onAppOpenAdShown(String placementId) {
			raiseEvent(ba, "on_app_open_ad_shown", placementId);
		}

		@Override
		public void onOfferWallAdClicked(String placementId) {
			raiseEvent(ba, "on_offer_wall_ad_clicked", placementId);
		}

		@Override
		public void onOfferWallAdClosed(String placementId) {
			raiseEvent(ba, "on_offer_wall_ad_closed", placementId);
		}

		@Override
		public void onOfferWallAdLoaded(String placementId) {
			raiseEvent(ba, "on_offer_wall_ad_loaded", placementId);
		}

		@Override
		public void onOfferWallAdShown(String placementId) {
			raiseEvent(ba, "on_offer_wall_ad_shown", placementId);
		}

		@Override
		public void onOfferWallMissionRewarded(String placementId, String currency, int rewardAmount) {
			raiseEvent(ba, "on_offer_wall_mission_rewarded", placementId, currency, rewardAmount);
		}
	}

}
