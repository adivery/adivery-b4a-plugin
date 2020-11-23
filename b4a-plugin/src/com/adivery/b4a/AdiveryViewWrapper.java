package com.adivery.b4a;

import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;
import anywheresoftware.b4a.objects.ViewWrapper;
import com.adivery.sdk.Adivery;

@Hide
public abstract class AdiveryViewWrapper extends ViewWrapper<View> {

  @Hide
  String prefix;

  @Hide
  public void initAd(BA ba, String rawPrefix, View object) {
    setObject(object);
    Initialize(ba, rawPrefix);
    this.prefix = rawPrefix.toLowerCase(BA.cul);
  }

  @Hide
  void raiseEvent(BA ba, String name) {
    ba.raiseEventFromDifferentThread(getObject(), null, 0, prefix + "_" + name, false, null);
  }
}
