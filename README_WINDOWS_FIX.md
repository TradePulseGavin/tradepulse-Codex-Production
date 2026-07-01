# Windows install fix

If the install fails on pandas, you are probably using a Python version without a ready-made pandas wheel for this project.

Best fix:

1. Install Python 3.12.
2. Delete the `.venv` folder inside this project if it exists.
3. Double-click `start_windows_py312`.
4. Open Chrome to `http://127.0.0.1:8000`.

If you do not want to install Python 3.12, try `start_windows`; it uses flexible package versions and prefers binary wheels.
