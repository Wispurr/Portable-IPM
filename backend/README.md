### Backend Server

-   Env: `Win 10`, `python-3.12.11`
-   Based: `fastapi`

    1. Create Virtual Env

        ```powershell
        python -m venv .venv
        ```

        ```powershell
        .venv\Scripts\Activate.ps1
        ```

    2. (OPTIONAL) Check Env is Active

        ```powershell
        Get-Command python
        ```

    3. Upgrade `pip`

        ```powershell
        python -m pip install --upgrade pip
        ```

    4. Update `.venv/` to `.gitignore`

        ```powershell
        echo "*" > .venv/.gitignore
        ```

    5. Install Package From `requirements.txt`

        ```powershell
        pip install -r requirements.txt
        ```

    6. Run Program

        ```powershell
        fastapi dev app.py
        ```

        as specific host and port

        ```powershell
        python .\app.py
        ```

    7. (ENDED) Deactivated Virtual Env

        ```powershell
        deactivate
        ```
