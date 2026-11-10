@echo off
pushd "%~dp0"
docker compose up --build -d --wait
if errorlevel 1 goto failed
docker compose exec -T dashboard python examples/presentation_studies.py --no-write --import-url http://127.0.0.1:8000
if errorlevel 1 goto failed
start "" "http://localhost:8000/experiments"
popd
exit /b 0
:failed
echo Study configuration import failed. Check the output above.
pause
popd
exit /b 1
