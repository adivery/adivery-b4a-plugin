package com.adivery.b4a;

import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;

@ShortName("Adivery")
@Permissions(values = { "android.permission.INTERNET" })
@DependsOn(values = { "Adivery.aar" })
@ActivityObject
public class Adivery {

  public static void Initialize(BA ba, String appId) {
    com.adivery.sdk.Adivery.configure(ba.activity.getApplication(), appId);
  }

  public static void SetLoggingEnabled(BA ba, boolean enabled) {
    com.adivery.sdk.Adivery.setLoggingEnabled(enabled);
  }
}
