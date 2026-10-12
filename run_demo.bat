@echo off
echo ==========================================
echo DEMO : GREAT EXPECTATIONS vs DATA OBSERVABILITY
echo ==========================================
python generate_data.py

echo.
echo ===== PARTIE 1 : GREAT EXPECTATIONS =====
python part1_great_expectations\gx_validation.py --batch clean
python part1_great_expectations\gx_validation.py --batch corrupted

echo.
echo ===== PARTIE 2 : DATA OBSERVABILITY =====
python part2_data_observability\observability.py --batch clean --reset
python part2_data_observability\observability.py --batch corrupted

echo.
echo Dashboard (partie 2) :
streamlit run part2_data_observability\dashboard.py
