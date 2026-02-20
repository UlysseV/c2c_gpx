# c2c_gpx

Export camptocamp search data to a gpx file intended for osmand or oruxmap.

## Install

```shell
python -m pip install c2c_gpx
```

This will add a new command `c2c_gpx` to your PATH.
Use `c2c_gpx -h` for help.


## How-To

Go to camptocamp.org and search for your document/activity/area of interest, add any filter you want.
When satisfied, use the url as a parameter to `c2c_gpx`:
```bash
c2c_gpx https://www.camptocamp.org/routes?bbox=1234,5678,9101,11213&act=rock_climbing -o my_routes.gpx
```

The resulting file can be opened in any map app.

## External ressources
- https://gpx.studio/app to see your gpx file online
- https://osmand.net/docs/technical/osmand-file-formats/osmand-gpx/
- https://www.camptocamp.org/articles/838875/en/api-c2c-v6
- https://github.com/c2corg/v6_api/wiki
