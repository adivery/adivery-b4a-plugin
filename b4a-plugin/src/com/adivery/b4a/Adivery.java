package com.adivery.b4a;

import com.adivery.sdk.networks.admob.AdMobAdapter;

import android.app.Application;
import anywheresoftware.b4a.BA;

@BA.ShortName("Adievry")
@BA.Version(1.0F)
@BA.Author("Adivery")
@BA.Events(
        values={}
)
@BA.ActivityObject
@BA.Permissions(values = {"android.permission.INTERNET"})
@BA.DependsOn(values=	{"adivery.aar","admob-adapter.aar"})
public class Adivery {

	@BA.Hide
	private static final String TAG = "ADIVERY";
	
	public static void initialize(BA ba, String appId) {
		Application app = ba.activity.getApplication();
		
		AdMobAdapter admobAdapter = null;
		
		try {
			Class.forName("com.google.android.gms.ads.MobileAds");
			admobAdapter = new AdMobAdapter();
		} catch (ClassNotFoundException ignored) {}
		
		if(admobAdapter!=null) {
			com.adivery.sdk.Adivery.configure(app, appId,admobAdapter);
		} else {
			com.adivery.sdk.Adivery.configure(app, appId);
		}
		
	}
	
	public static void setLoggingEnabled(BA ba, boolean enabled) {
		com.adivery.sdk.Adivery.setLoggingEnabled(enabled);
	}
}
