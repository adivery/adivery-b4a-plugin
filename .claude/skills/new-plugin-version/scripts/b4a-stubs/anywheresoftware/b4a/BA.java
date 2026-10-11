package anywheresoftware.b4a;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.util.Locale;

/**
 * Compile-only stand-in for B4A's anywheresoftware.b4a.BA (Core.jar), so `bridge.py compile` can
 * type-check the plugin against an SDK AAR on Linux. It declares only what the plugin uses. It is
 * NOT the real API: when a member is missing here, add it with the real signature, and never treat
 * a stub compile as proof that the B4A side compiles (pass --core-jar for that).
 */
public class BA {
	public Context context;
	public Activity activity;
	public static Application applicationContext;
	public static Locale cul = Locale.US;

	// Returns Object in Core.jar (descriptor ...Z[Ljava/lang/Object;)Ljava/lang/Object;, as the
	// published Adivery.jar calls it).
	public Object raiseEventFromDifferentThread(Object sender, Object container, int TaskId, String event,
			boolean throwErrorIfMissingSub, Object[] params) {
		return null;
	}

	public Object raiseEvent(Object sender, String event, Object... params) {
		return null;
	}

	public boolean subExists(String sub) {
		return false;
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface ShortName {
		String value();
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface Version {
		float value();
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface Author {
		String value();
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface Permissions {
		String[] values();
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface DependsOn {
		String[] values();
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface Events {
		String[] values();
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface ActivityObject {
	}

	@Retention(RetentionPolicy.RUNTIME)
	public @interface Hide {
	}
}
