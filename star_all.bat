@echo off

start "Orquestador" cmd /k cd /d "C:\Users\alfre\OneDrive\Escritorio\9no Semestre\Servicios Web\ProyectoSoa\middleware" ^&^& python orquestador.py ^& pause

start "Microservicio Auth" cmd /k cd /d "C:\Users\alfre\OneDrive\Escritorio\9no Semestre\Servicios Web\ProyectoSoa\auth_service" ^&^& python consumer_auth.py ^& pause

start "Microservicio SQL" cmd /k cd /d "C:\Users\alfre\OneDrive\Escritorio\9no Semestre\Servicios Web\ProyectoSoa\crud_service" ^&^& python consumer_crud.py ^& pause

start "Microservicio NoSQL" cmd /k cd /d "C:\Users\alfre\OneDrive\Escritorio\9no Semestre\Servicios Web\ProyectoSoa\consumer_nosql" ^&^& python consumer_nosql.py ^& pause

start "Microservicio Roles" cmd /k cd /d "C:\Users\alfre\OneDrive\Escritorio\9no Semestre\Servicios Web\ProyectoSoa\consumer_roles" ^&^& python consumer_roles.py ^& pause
