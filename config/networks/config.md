# Configuración de pysim

El archivo config define los enlaces WiFi entre nodos. El formato del archivo es el siguiente:

```json
{
  "NodeName": {
    "n": "{NodeName}.{Orientation}",
    "e": "{NodeName}.{Orientation}",
    "s": "{NodeName}.{Orientation}",
    "w": "{NodeName}.{Orientation}"
  }
}
```

Por ejemplo, para una red que tiene 3 nodos `{root, Re, Rs}` y con conexiones entre `root` y `Re` por este/oeste, entre
`root` y `Rs` por norte/sur y entre `Re` y `Rs` por sur/este el archivo quedaría así:

```json
{
  "re": {
    "w": "root.e"
  },
  "rs": {
    "n": "root.s",
    "e": "re.s"
  }
}
```

Notar que:

- La presencia o ausencia de un dispositivo (`nodo+orientación`) en el archivo de configuración implica el modo de WiFi
  utilizado por el dispositivo. Aquellos que estén presentes en el archivo de configuración (es decir, tienen un enlace
  asignado) serán STATION, mientras que aquellos que no estén serán APs.
- En el ejemplo anterior, `re.w` y `rs.{n, e}` actuarán como STATION, mientras que `re.{n, s, e}` y `rs.{s, w}`
  actuarán como APs.
- Los dispositivos del `root` sólo pueden actuar como APs.
- Las conexiones **no** se establecen al inicio del programa sino que se establecen cuando el sistema de ruteo lo
  considere oportuno igual que en la "vida real". Esta configuración sólo sirve para simplificar la simulación dándole
  un rol único a cada interfaz WiFi.
- Todo nodo no-root deberá estar presente en el archivo de configuración, ya que, como mínimo _uno_ de sus dispositivos
  deberá estar en modo STATION.