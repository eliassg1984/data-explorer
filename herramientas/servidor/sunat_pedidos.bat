@echo off
REM ===========================================================================
REM sunat_pedidos.bat — atiende los pedidos que deja la webapp.
REM Programar CADA MINUTO en el Programador de tareas de Windows.
REM
REM Si no hay pedidos sale en ~1 segundo y NO abre el navegador, asi que
REM correrlo tan seguido no cuesta nada.
REM
REM OJO con el usuario: los paquetes de Python (pandas, playwright) y el
REM Chromium quedaron instalados bajo el perfil de Administrador. La tarea
REM programada TIENE que correr con ese mismo usuario, o falla con
REM "No module named pandas".
REM ===========================================================================

REM Ruta completa al python.exe: el Programador de tareas no siempre hereda
REM el PATH del usuario, asi que confiar en un "python" pelado falla en
REM produccion aunque funcione al probarlo a mano en la consola.
set PYTHON="C:\Users\Administrador\AppData\Local\Programs\Python\Python312\python.exe"

cd /d C:\proyecto
if not exist logs mkdir logs

%PYTHON% sunat_originales.py --pedidos >> logs\sunat_pedidos.txt 2>&1
