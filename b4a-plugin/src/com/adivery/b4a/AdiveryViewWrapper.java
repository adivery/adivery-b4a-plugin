package com.adivery.b4a;

import android.view.View;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;
import anywheresoftware.b4a.objects.ViewWrapper;

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
  
  @Hide
  void raiseEvent(BA ba, String name, Object... param) {
	ba.raiseEventFromDifferentThread(getObject(), null, 0, prefix  + "_" + name, false, param);
  }
}
