try:
    import vizu_models
    print("Successfully imported vizu_models")
except Exception as e:
    import traceback
    print("Failed to import vizu_models")
    traceback.print_exc()
