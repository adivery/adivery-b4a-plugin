package com.adivery.b4a;

import com.adivery.sdk.Adivery;
import com.adivery.sdk.AdiveryLoadedAd;
import com.adivery.sdk.AdiveryRewardedCallback;

import android.util.Log;
import android.view.View;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.ActivityObject;
import anywheresoftware.b4a.BA.Events;
import anywheresoftware.b4a.BA.Hide;
import anywheresoftware.b4a.BA.ShortName;
import anywheresoftware.b4a.objects.ViewWrapper;

@ShortName("AdiveryRewardedAd")
@ActivityObject
@Events(values = {
		"AdLoaded",
		"AdClicked",
		"AdLoadFailed",
		"AdShowFailed",
		"AdClosed",
		"AdShown",
		"AdRewarded"
})
public class AdiveryRewardedAd extends ViewWrapper<View> {
	
	@Hide()
	private AdiveryLoadedAd ad;
	
	public void initialize2(BA ba,String EventName,String placementId) {
		ad = null;
		Log.d("Adivery","initializing rewarded");
		View view = new View(ba.context);
		setObject(view);
		Initialize(ba, EventName);
		final String eventName = EventName.toLowerCase(BA.cul);
		Adivery.requestRewardedAd(ba.activity, placementId, new AdiveryRewardedCallback() {
			@Override
			public void onAdLoaded(AdiveryLoadedAd ad) {
				Log.d("Adivery","rewarded loaded");
				AdiveryRewardedAd.this.ad = ad;
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adloaded", false, null);
			}
			
			@Override
			public void onAdClicked() {
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adclicked", false, null);
			}
			
			@Override
			public void onAdClosed() {
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adclosed", false, null);
			}
			
			@Override
			public void onAdLoadFailed(int errorCode) {
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adloadfailed", false, null);
			}
			
			@Override
			public void onAdRewarded() {
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adrewarded", false, null);
			}
			
			@Override
			public void onAdShowFailed(int errorCode) {
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adshowfailed", false, null);
			}
			
			@Override
			public void onAdShown() {
				ba.raiseEventFromDifferentThread(getObject(), null, 0, String.valueOf(eventName) + "_adshown", false, null);

			}
		});
	}
	
	public boolean isLoaded(BA ba) {
		return ad!=null;
	}
	
	public void showAd(BA ba) {
		if(ad!=null) {
			ad.show();
		}
	}
}
