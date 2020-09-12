package com.adivery.b4a;

import com.adivery.sdk.Adivery;
import com.adivery.sdk.AdiveryBannerCallback;
import com.adivery.sdk.BannerType;

import android.util.Log;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.view.View;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.objects.ViewWrapper;
import anywheresoftware.b4a.BA.ActivityObject;
import anywheresoftware.b4a.BA.Events;
import anywheresoftware.b4a.BA.ShortName;

@ShortName("AdiveryBannerAd")
@ActivityObject
@Events(values = {
		"AdLoaded",
		"AdClicked",
		"AdLoadFailed",
		"AdShowFailed"
})
// Event names in annotations must be CamelCase and event names in raise methods must be lower case
public class AdiveryBannerAd extends ViewWrapper<ViewGroup> {
	
	public void initialize2(BA ba,String EventName,String placementId,String bannerType) {
		ViewGroup vg = new FrameLayout(ba.context);
		setObject(vg);
		Initialize(ba, EventName);
		final String eventName = EventName.toLowerCase(BA.cul);
		Adivery.requestBannerAd(ba.activity, placementId, getBannerType(bannerType), new AdiveryBannerCallback() {
			@Override
			public void onAdLoaded(View adView) {
				Log.d("Adivery","banner loaded");
				vg.addView(adView);
				ba.raiseEventFromDifferentThread(AdiveryBannerAd.this.getObject(), null, 0, String.valueOf(eventName) + "_adloaded", false, null);
			}
			
			@Override
			public void onAdClicked() {
				ba.raiseEventFromDifferentThread(AdiveryBannerAd.this.getObject(), null, 0, String.valueOf(eventName) + "_adclicked", false, null);
			}
			
			@Override
			public void onAdLoadFailed(int errorCode) {
				ba.raiseEventFromDifferentThread(AdiveryBannerAd.this.getObject(), null, 0, String.valueOf(eventName) + "_adloadfailed", false, null);
			}
			
			@Override
			public void onAdShowFailed(int errorCode) {
				ba.raiseEventFromDifferentThread(AdiveryBannerAd.this.getObject(), null, 0, String.valueOf(eventName) + "_adshowfailed", false, null);
			}
		});
	}
	
	private static BannerType getBannerType(String type) {
		if(type.equalsIgnoreCase("banner")) {
			return BannerType.BANNER;
		} else if(type.equalsIgnoreCase("large_banner")) {
			return BannerType.LARGE_BANNER;
		} else {
			return BannerType.MEDIUM_RECTANGLE;
		}
	}
}
