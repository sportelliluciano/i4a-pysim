# Simulación para Internet4All

Este repositorio incluye dos simulaciones para Internet4All:

- Una simulación teórica, diseñada para realizar pruebas sobre el algoritmo de ruteo
- Una simulación completa, que corre el código de los nodos en QEMU

Para lanzar la simulación teórica:

- Editar el archivo `config/config.json` para elegir la red a simular.
- Editar el archivo `docker-compose.yml` y sacar `--qemu` en los comandos de los servicios
  `node-root` y `node-home`.
- En el mismo archivo, cambiar la cantidad de réplicas del `nodo-home` por la cantidad necesaria
  para simular la red elegida.
- Lanzar la simulación con `docker compose up`.
- Ingresar a `localhost:8000` para acceder a la UI de la simulación.

Para lanzar la simulación práctica:

- Elegir la red a simular igual que en el caso anterior. Notar que esta simulación requiere
  significativamente más recursos, se sugiere utilizar una red con 2-5 nodos.
- Editar el archivo `docker-compose.yml` y agregar `--qemu` a la línea de comandos de los servicios
  `node-root` y `node-home`.
- Actualiar la cantidad de réplicas según la red elegida
- Utilizar el comando `idf.py qemu gdb` para compilar el código del proyecto para QEMU. Al
  finalizar se inciará una instancia de gdb con el código cargado, la misma es útil para buscar
  símbolos en caso de que el emulador se reinicie por un problema en el código, pero si no se
  utiliza puede simplemente cerrarse.
- Actualizar en el archivo compose las rutas a la carpeta `build` del código del proyecto, de
  aquí se tomarán los archivos `qemu_flash.bin` y `qemu_efuse.bin` para utilizar en QEMU.
- Lanzar la simulación con `docker compose up`
- Acceder a la UI en `localhost:8000`
