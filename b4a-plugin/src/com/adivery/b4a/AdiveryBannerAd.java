package com.adivery.b4a;

import android.widget.FrameLayout;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;
import com.adivery.sdk.AdiveryBannerAdView;
import com.adivery.sdk.AdiveryAdListener;
import com.adivery.sdk.BannerSize;

@ShortName("AdiveryBannerAd")
@Events(values = { "Ad_Loaded", "Ad_Clicked", "Ad_Error (error As String)" })
@ActivityObject
public class AdiveryBannerAd extends AdiveryViewWrapper {

  public static Object BANNER = BannerSize.BANNER;
  public static Object LARGE_BANNER = BannerSize.LARGE_BANNER;
  public static Object MEDIUM_RECTANGLE = BannerSize.MEDIUM_RECTANGLE;
  public static Object SMART_BANNER = BannerSize.SMART_BANNER;

  public void Initialize2(final BA ba, String rawPrefix, String placementId, Object bannerSize) {
    final FrameLayout container = new FrameLayout(ba.context);
    initAd(ba, rawPrefix, container);
    
    AdiveryBannerAdView adView = new AdiveryBannerAdView(ba.activity);
    adView.setBannerSize((BannerSize) bannerSize);
    adView.loadAd(placementId);
    adView.setBannerAdListener(new AdiveryAdListener() {
		
		@Override
		public void onError(String reason) {
			raiseEvent(ba, "ad_error", reason);
			
		}
		
		@Override
		public void onAdClicked() {
			raiseEvent(ba, "ad_clicked");
			
		}
		
		@Override
		public void onAdLoaded() {
			raiseEvent(ba, "ad_loaded");
			container.addView(adView);
		}
	});
  }
}
