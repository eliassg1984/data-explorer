@echo off
REM ===========================================================================
REM sunat_nocturno.bat — baja los PDF/XML que faltan, de lo mas nuevo hacia
REM atras. Programar UNA VEZ POR NOCHE.
REM
REM Atiende primero los pedidos que haya (alguien esta esperando) y con el
REM tiempo que sobra hace el backfill. Corta solo a los 120 minutos.
REM
REM Medido en el servidor: ~23 segundos por documento, o sea ~313 por noche.
REM Con 9.813 pendientes son ~31 noches para cubrirlos todos. Para ir mas
REM rapido las primeras semanas, subir --minutos a 240 (~16 noches).
REM
REM OJO con el usuario: los paquetes de Python y el Chromium quedaron bajo
REM el perfil de Administrador. La tarea programada TIENE que correr con ese
REM mismo usuario, o falla con "No module named pandas".
REM ===========================================================================

REM Ruta completa al python.exe: el Programador de tareas no siempre hereda
REM el PATH del usuario, asi que confiar en un "python" pelado falla en
REM produccion aunque funcione al probarlo a mano en la consola.
set PYTHON="C:\Users\Administrador\AppData\Local\Programs\Python\Python312\python.exe"

cd /d C:\proyecto
if not exist logs mkdir logs

REM El log se ACUMULA (>>) y no se pisa: cuando algo falle, lo que importa es
REM poder mirar las noches anteriores para ver desde cuando viene mal.
echo. >> logs\sunat_nocturno.txt
echo ===== %date% %time% ===== >> logs\sunat_nocturno.txt
%PYTHON% sunat_originales.py --minutos 120 >> logs\sunat_nocturno.txt 2>&1
