package com.adivery.b4a;

import android.app.Activity;
import android.app.Application;
import android.os.Bundle;
import anywheresoftware.b4a.BA;
import anywheresoftware.b4a.BA.*;

@Hide
public class ActivityChangeListener implements Application.ActivityLifecycleCallbacks {

	interface OnActivityChangedListener {
		void onActivityChanged(String name);
	}

	public static Activity activity;

	OnActivityChangedListener listener;

	public ActivityChangeListener(OnActivityChangedListener listener) {
		this.listener = listener;
	}

	@Override
	public void onActivityCreated(Activity activity, Bundle savedInstanceState) {
		ActivityChangeListener.activity = activity;
	}

	@Override
	public void onActivityDestroyed(Activity activity) {
	}

	@Override
	public void onActivityPaused(Activity activity) {
	}

	@Override
	public void onActivityResumed(Activity activity) {
		// Ad activities (Adivery's AdActivity and DeepLinkActivity, mediated networks' own) aren't B4A
		// activities: keep raising events to the B4A activity below them. B4A activities live in the app's package.
		if (!activity.getClass().getName().startsWith(BA.packageName + ".")) {
			return;
		}
		listener.onActivityChanged(activity.getClass().getSimpleName());
		ActivityChangeListener.activity = activity;
	}

	@Override
	public void onActivitySaveInstanceState(Activity activity, Bundle outState) {
	}

	@Override
	public void onActivityStarted(Activity activity) {
		ActivityChangeListener.activity = activity;
	}

	@Override
	public void onActivityStopped(Activity activity) {
	}
}
