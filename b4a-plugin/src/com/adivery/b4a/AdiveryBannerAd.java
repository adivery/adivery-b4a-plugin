package com.adivery.b4a;

import android.util.Log;
import android.view.View;
import android.widget.FrameLayout;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;
import com.adivery.sdk.Adivery;
import com.adivery.sdk.AdiveryBannerCallback;
import com.adivery.sdk.BannerType;

@ShortName("AdiveryBannerAd")
@Events(values = { "AdLoaded", "AdClicked", "AdLoadFailed", "AdShowFailed" })
@ActivityObject
public class AdiveryBannerAd extends AdiveryViewWrapper {

  public static Object BANNER = BannerType.BANNER;
  public static Object LARGE_BANNER = BannerType.LARGE_BANNER;
  public static Object MEDIUM_RECTANGLE = BannerType.MEDIUM_RECTANGLE;
  public static Object FLEX_BANNER = BannerType.FLEX_BANNER;

  public void Initialize2(final BA ba, String rawPrefix, String placementId, Object bannerType) {
    final FrameLayout container = new FrameLayout(ba.context);
    initAd(ba, rawPrefix, container);

    Adivery.requestBannerAd(
      ba.context,
      placementId,
      (BannerType) bannerType,
      new AdiveryBannerCallback() {
        @Override
        public void onAdLoaded(View adView) {
          container.addView(adView);
          raiseEvent(ba, "adloaded");
        }

        @Override
        public void onAdClicked() {
          raiseEvent(ba, "adclicked");
        }

        @Override
        public void onAdLoadFailed(int errorCode) {
          raiseEvent(ba, "adloadfailed");
        }

        @Override
        public void onAdShowFailed(int errorCode) {
          raiseEvent(ba, "adshowfailed");
        }
      }
    );
  }
}
