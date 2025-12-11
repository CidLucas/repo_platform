try:
    import vizu_models  # noqa: F401
    print("Successfully imported vizu_models")
except Exception:
    import traceback
    print("Failed to import vizu_models")
    traceback.print_exc()
