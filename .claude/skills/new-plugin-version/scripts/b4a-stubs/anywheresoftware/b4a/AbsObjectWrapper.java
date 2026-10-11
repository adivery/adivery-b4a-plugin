package anywheresoftware.b4a;

/** Compile-only stand-in for B4A's AbsObjectWrapper (Core.jar). See BA.java. */
public abstract class AbsObjectWrapper<T> {
	private T object;

	public void setObject(T object) {
		this.object = object;
	}

	public T getObject() {
		return object;
	}

	public boolean IsInitialized() {
		return object != null;
	}
}
