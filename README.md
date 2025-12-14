# Simulación para Internet4All

Este repositorio incluye dos simulaciones para Internet4All:

- Una simulación teórica, diseñada para realizar pruebas sobre el algoritmo de ruteo
- Una simulación completa, que corre el código de los nodos en QEMU

Para lanzar la simulación teórica:

- Editar el archivo `config/config.json` para elegir la red a simular.
- Setear la variable de entorno `I4A_HOME_NODES_COUNT` a la cantidad de nodos "home" requerida. Este valor depende de la red elegida en la configuración. Por ejemplo, para la red `basic`, sería `I4A_HOME_NODES_COUNT=2`.
- Lanzar la simulación con `docker compose up`.
- Ingresar a `localhost:8000` para acceder a la UI de la simulación.

Para lanzar la simulación práctica:

- Elegir la red a simular y la cantidad de nodos "home" igual que en el caso anterior. Notar que esta 
  simulación requiere significativamente más recursos, se sugiere utilizar una red con 2-5 nodos.
- Setear la variable de entorno `I4A_EXTRA_NODE_ARGS="--qemu"`.
- Setear la variable de entorno `QEMU_BUILD_PATH` con la ruta a la carpeta `build` del código del proyecto, de
  aquí se tomarán los archivos `qemu_flash.bin` y `qemu_efuse.bin` para utilizar en QEMU. Por ejemplo, `QEMU_BUILD_PATH=/home/luciano/i4a/tests/full_integration/build`.
- Utilizar el comando `idf.py qemu gdb` para compilar el código del proyecto para QEMU. Al
  finalizar se inciará una instancia de gdb con el código cargado, la misma es útil para buscar
  símbolos en caso de que el emulador se reinicie por un problema en el código, pero si no se
  utiliza puede simplemente cerrarse.
- Lanzar la simulación con `docker compose up`
- Acceder a la UI en `localhost:8000`
