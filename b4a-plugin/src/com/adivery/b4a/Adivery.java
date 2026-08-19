package com.adivery.b4a;

import com.adivery.sdk.AdiveryListener;

import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;

@ShortName("Adivery")
@Version(4.9f)
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

	public static void Initialize(BA ba, String appId) {
		com.adivery.sdk.Adivery.configure(ba.activity.getApplication(), appId);
		addListener(ba);
	}

	public static void SetLoggingEnabled(BA ba, boolean enabled) {
		com.adivery.sdk.Adivery.setLoggingEnabled(enabled);
	}

	public static void SetUserId(BA ba, String userId) {
		com.adivery.sdk.Adivery.setUserId(userId);
	}

	public static void PrepareInterstitialAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareInterstitialAd(ba.activity, placementId);
	}

	public static void PrepareRewardedAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareRewardedAd(ba.activity, placementId);
	}

	public static void PrepareAppOpenAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareAppOpenAd(ba.activity, placementId);
	}

	public static void ShowAppOpenAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.showAppOpenAd(ba.activity, placementId);
	}

	public static void PrepareOfferWallAd(BA ba, String placementId) {
		com.adivery.sdk.Adivery.prepareOfferWallAd(ba.activity, placementId);
	}

	public static void Show(BA ba, String placementId) {
		com.adivery.sdk.Adivery.showAd(placementId);
	}

	public static boolean IsLoaded(BA ba, String placementId) {
		return com.adivery.sdk.Adivery.isLoaded(placementId);
	}

	private static void addListener(BA ba) {
		com.adivery.sdk.Adivery.addListener(new AdiveryListener() {
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
		});
	}

	public static void raiseEvent(BA ba, String name, Object... params) {
		ba.raiseEventFromDifferentThread(Adivery.class, ba, 0, name, false, params);
	}

}
