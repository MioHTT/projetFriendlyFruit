var res = "";

mapboxgl.accessToken = 'pk.eyJ1IjoiZnJpZW5kbHlmcnVpdHMxIiwiYSI6ImNrY3VoYXc5cjB6bGcydG80cmVpY3RqbGkifQ.EC5KmCbDEBeVgFHjYXIgzA';
const container = document.getElementById('map')
window.addEventListener("load", createMap);

function createMap() {
    if (typeof areas !== "undefined") {
        var distanceContainer = document.getElementById('distance-info');

        // GeoJSON object to hold our measurement features
        var geojson = {
            'type': 'FeatureCollection',
            'features': []
        };

        // Used to draw a line between points
        var linestring = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': []
            }
        };
        // document.getElementById("count_areas").innerHTML += "<br> Zone(s) trouvée(s) : " + areas.length + "<br>"
        document.getElementById("count_areas").innerHTML += "<br> Zone(s) en Water Deficit : " + areas.filter(x => x[2] === 'WD').length  

        container2 = document.getElementById('map')
        // container2.style.display = "none"
        var map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/satellite-v9',
            center: areas[0][1][0],
            zoom: 18
        });

        map.on('load', function () {
            map.addSource('geojson', {
                'type': 'geojson',
                'data': geojson
            });

            // Add styles to the map
            map.addLayer({
                id: 'measure-points',
                type: 'circle',
                source: 'geojson',
                paint: {
                    'circle-radius': 5,
                    'circle-color': 'blue',
                },
                filter: ['in', '$type', 'Point']
            });
            map.addLayer({
                id: 'measure-lines',
                type: 'line',
                source: 'geojson',
                layout: {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                paint: {
                    'line-color': 'blue',
                    'line-width': 2.5
                },
                filter: ['in', '$type', 'LineString']
            });

            map.on('click', function (e) {
                var features = map.queryRenderedFeatures(e.point, {
                    layers: ['measure-points']
                });

                // Remove the linestring from the group
                // So we can redraw it based on the points collection
                if (geojson.features.length > 1) geojson.features.pop();

                // Clear the Distance container to populate it with a new value
                distanceContainer.innerHTML = '';

                // If a feature was clicked, remove it from the map
                if (features.length) {
                    var id = features[0].properties.id;
                    geojson.features = geojson.features.filter(function (point) {
                        return point.properties.id !== id;
                    });
                } else {
                    var point = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [e.lngLat.lng, e.lngLat.lat]
                        },
                        'properties': {
                            'id': String(new Date().getTime())
                        }
                    };

                    geojson.features.push(point);
                }

                if (geojson.features.length > 1) {
                    linestring.geometry.coordinates = geojson.features.map(function (
                        point
                    ) {
                        return point.geometry.coordinates;
                    });

                    geojson.features.push(linestring);

                    // Populate the distanceContainer with total distance
                    var value = document.getElementById('distance-info');
                    distToMeter =  turf.length(linestring)*1000
                    value.textContent =
                        'Distance: ' +
                        distToMeter.toLocaleString() +
                        'm';
                }

                map.getSource('geojson').setData(geojson);
            });
            for (coordonnees of areas) {
                console.log(coordonnees)
                map.addSource(coordonnees[0], {
                    'type': 'geojson',
                    'data': {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coordonnees[1]]
                        },
                        properties: {
                            'coordinates': coordonnees[1],
                            'water-type': coordonnees[2],
                        },

                    }
                });
                fillcolor = (coordonnees[2] == "OW" ? 'blue' : 'red')
                map.addLayer({
                    'id': coordonnees[0],
                    'type': 'fill',
                    'source': coordonnees[0],
                    'layout': {},
                    'paint': {
                        'fill-color': fillcolor,
                        'fill-opacity': 0.8
                    }
                });


                // Change the cursor to a pointer when the mouse is over the states layer.
                map.on('mouseenter', coordonnees[0], function () {
                    map.getCanvas().style.cursor = 'pointer';
                });

                // Change it back to a pointer when it leaves.
                map.on('mouseleave', coordonnees[0], function () {
                    map.getCanvas().style.cursor = '';
                });
                map.on('mousemove', coordonnees[0], function (e) {
                    var distanceFeatures = map.queryRenderedFeatures(e.point, {
                        layers: ['measure-points']
                        });
                        // UI indicator for clicking/hovering a point on the map
                        map.getCanvas().style.cursor = distanceFeatures.length
                        ? 'pointer'
                        : 'crosshair';
                    var features = map.queryRenderedFeatures(e.point);
                    // Limit the number of properties we're displaying for
                    // legibility and performance
                    var displayProperties = [
                        'source',
                        'properties',
                    ];
                    var displayFeatures = features.map(function (feat) {
                        var displayFeat = {};
                        displayProperties.forEach(function (prop) {
                            displayFeat[prop] = feat[prop];
                        });
                        return displayFeat;
                    });

                    document.getElementById('features-info').innerHTML =
                        "Nom :  <br> " + displayFeatures[0]['source'] + '<br>' +
                        "Water Type :  <br> " + displayFeatures[0]['properties']['water-type']
                        + '<br>' +
                        "Coordonnées du polygone     : <br> " + displayFeatures[0]['properties']['coordinates'].replaceAll("],[", "]<br>[")

                });
            }
        });
    }
}