package com.adivery.b4a;

import android.view.View;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;
import com.adivery.sdk.Adivery;
import com.adivery.sdk.AdiveryInterstitialCallback;
import com.adivery.sdk.AdiveryLoadedAd;

@ShortName("AdiveryInterstitialAd")
@Events(
  values = {
    "AdLoaded",
    "AdClicked",
    "AdLoadFailed",
    "AdShowFailed",
    "AdClosed",
    "AdShown",
  }
)
@ActivityObject
public class AdiveryInterstitialAd extends AdiveryViewWrapper {

  @Hide
  private AdiveryLoadedAd ad;

  public void Initialize2(final BA ba, String rawPrefix, String placementId) {
    initAd(ba, rawPrefix, new View(ba.context));

    Adivery.requestInterstitialAd(
      ba.activity,
      placementId,
      new AdiveryInterstitialCallback() {
        @Override
        public void onAdLoaded(AdiveryLoadedAd loadedAd) {
          ad = loadedAd;
          raiseEvent(ba, "adloaded");
        }

        @Override
        public void onAdClicked() {
          raiseEvent(ba, "adclicked");
        }

        @Override
        public void onAdClosed() {
          raiseEvent(ba, "adclosed");
        }

        @Override
        public void onAdLoadFailed(int errorCode) {
          raiseEvent(ba, "adloadfailed");
        }

        @Override
        public void onAdShowFailed(int errorCode) {
          raiseEvent(ba, "adshowfailed");
        }

        @Override
        public void onAdShown() {
          raiseEvent(ba, "adshown");
        }
      }
    );
  }

  public boolean IsLoaded(BA ba) {
    return ad != null;
  }

  public void ShowAd(BA ba) {
    if (this.ad != null) {
      this.ad.show();
      this.ad = null;
    }
  }
}
