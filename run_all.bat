@echo off
echo ==========================================
echo RKTN パイプラインを実行しています...
echo ==========================================
cd /d %~dp0
python src/run_all.py
echo.
echo 実行が完了しました。
pause
