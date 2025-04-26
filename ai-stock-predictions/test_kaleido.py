# test_kaleido.py
import plotly.graph_objects as go
import os
import time
import sys # Import sys for path info

print(f"Using Python: {sys.executable}") # Shows which python is running
print("Creating simple figure...")
fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[2, 1, 3]))
fig.update_layout(title="Kaleido Test Chart") # Add a title

output_dir = "static_test"
try: # Use try-except for directory creation
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {os.path.abspath(output_dir)}")
except Exception as e:
    print(f"Error creating directory {output_dir}: {e}")
    exit()

output_path = os.path.join(output_dir, "test_image.png")

print(f"Attempting to save image to: {output_path}")
try:
    start_time = time.time()
    # Add engine='kaleido' explicitly, though it's default
    fig.write_image(output_path, engine='kaleido')
    end_time = time.time()
    print(f"Successfully saved image in {end_time - start_time:.2f} seconds.")
    print(f"Check for the file at: {os.path.abspath(output_path)}")
except Exception as e:
    print(f"----- ERROR SAVING IMAGE -----")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    print(f"-----------------------------")

print("Test finished.")