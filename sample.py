def sample(speed=None, **kwargs):
    """
    Executes logic based on the keyword arguments passed from the main interpreter.
    """
    print("\n--- Executing sample.py ---")

    if speed is not None:
        print(f"Action: Running sample script. Speed confirmed at: {speed}")
    else:
        print("Action: Running sample script with default speed.")

    # Catch any additional parameters passed from the document
    if kwargs:
        for key, value in kwargs.items():
            print(f"Additional parameter received -> {key}: {value}")

    print("--- Finished sample.py ---\n")


# Optional: Allow the script to be run independently for testing
if __name__ == "__main__":
    sample(speed=5, velocity=15)
