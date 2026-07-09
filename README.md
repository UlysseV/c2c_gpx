# c2c_gpx

Export camptocamp search data to a gpx file intended for osmand or oruxmap.

## Install

```shell
python -m pip install c2c_gpx
```

This will add a new command `c2c_gpx` to your PATH.
Use `c2c_gpx -h` for help.


## How-To

Go to camptocamp.org and search for your document/activity/area of interest.
Check "Filter on map extent" and add any filter you want.
When satisfied, use the url as a parameter to `c2c_gpx`:
```bash
c2c_gpx "https://www.camptocamp.org/routes?bbox=1234,5678,9101,11213&act=rock_climbing" -o my_routes.gpx
```
Note: quotes around the url are important for the `&` to be passed down correctly.

The resulting file can be opened in any map app.


### Exporting your stared routes

You can add the url parameter `u=[use_id]` to the routes (resp. outings) search url to limit the search to your favorite routes (resp. own outings).
For example, if you want to extract the starred ski touring routes of user `1234`, use the following:
```bash
c2c_gpx "https://www.camptocamp.org/routes?u=1234&act=skitouring"
```

### Exporting routes associated to a book or waypoint

You can use the url of a book or a waypoint to exports the routes associated with it.
For instance, here is how to extract the routes departing from the *refuge Temple Écrin*:
```bash
c2c_gpx "https://www.camptocamp.org/waypoints/104028/fr/refuge-temple-ecrins"
```
And here is the complete set of routes listed in the book *Oisan nouveau Oisan sauvage - livre Est*:
```bash
c2c_gpx "https://www.camptocamp.org/books/14637/fr/oisans-nouveau-oisans-sauvage-livre-est"
```


## External ressources
- https://gpx.studio/app to see your gpx file online
- https://osmand.net/docs/technical/osmand-file-formats/osmand-gpx/
- https://www.camptocamp.org/articles/838875/en/api-c2c-v6
- https://github.com/c2corg/v6_api/wiki
