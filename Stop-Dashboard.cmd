@echo off
pushd "%~dp0"
docker compose stop
if errorlevel 1 pause
popd
