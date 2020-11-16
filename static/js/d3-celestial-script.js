var config = {
  width: 0,           // Default width, 0 = full parent element width;
                      // height is determined by projection
  projection: "aitoff",    // Map projection used: see below
  transform: "equatorial", // Coordinate transformation: equatorial (default),
                           // ecliptic, galactic, supergalactic
  center: null,       // Initial center coordinates in set transform
                      // [longitude, latitude, orientation] all in degrees
                      // null = default center [0,0,0]
  orientationfixed: true,  // Keep orientation angle the same as center[2]
  geopos: null,       // optional initial geographic position [lat,lon] in degrees,
                      // overrides center
  follow: "center",   // on which coordinates to center the map, default: zenith, if location enabled,
                      // otherwise center
  zoomlevel: null,    // initial zoom level 0...zoomextend; 0|null = default, 1 = 100%, 0 < x <= zoomextend
  zoomextend: 10,     // maximum zoom level
  adaptable: true,    // Sizes are increased with higher zoom-levels
  interactive: true,  // Enable zooming and rotation with mousewheel and dragging
  form: false,         // Display form for interactive settings. Needs a div with
                      // id="celestial-form", created automatically if not present
  location: false,    // Display location settings. Deprecated, use formFields below
  formFields: {"location": true,  // Set visiblity for each group of fields with the respective id
               "general": true,
               "stars": true,
               "dsos": true,
               "constellations": true,
               "lines": true,
               "other": true},
                      // Needs a div with id="celestial-form"
  daterange: [],      // Calender date range; null: displaydate-+10; [n<100]: displaydate-+n; [yr]: yr-+10;
                      // [yr, n<100]: [yr-n, yr+n]; [yr0, yr1]
  controls: true,     // Display zoom controls
  lang: "",           // Language for names, so far only for constellations:
                      // de: german, es: spanish. Default:en or empty string for english
  culture: "",        // Source of constellations and star names, default "iau", other: "cn" Traditional Chinese
  container: "celestial-map",   // ID of parent element, e.g. div, null = html-body
  datapath: document.getElementById('d3CelestialScript').getAttribute('staticUrl') + 'vendor/d3-celestial/data/',  // Path/URL to data files, empty = subfolder 'data'
  stars: {
    show: false,    // Show stars
    limit: 6,      // Show only stars brighter than limit magnitude
    colors: true,  // Show stars in spectral colors, if not use default color
    style: { fill: "#ffffff", opacity: 1 }, // Style for stars
    designation: true, // Show star names (Bayer, Flamsteed, Variable star, Gliese or designation,
                       // i.e. whichever of the previous applies first); may vary with culture setting
    designationType: "desig",  // Which kind of name is displayed as designation (fieldname in starnames.json)
    designationStyle: { fill: "#ddddbb", font: "11px 'Palatino Linotype', Georgia, Times, 'Times Roman', serif", align: "left", baseline: "top" },
    designationLimit: 2.5,  // Show only names for stars brighter than nameLimit
    propername: false,   // Show proper name (if present)
    propernameType: "name", // Field in starnames.json that contains proper name; may vary with culture setting
    propernameStyle: { fill: "#ddddbb", font: "13px 'Palatino Linotype', Georgia, Times, 'Times Roman', serif", align: "right", baseline: "bottom" },
    propernameLimit: 1.5,  // Show proper names for stars brighter than propernameLimit
    size: 7,       // Maximum size (radius) of star circle in pixels
    exponent: -0.28, // Scale exponent for star size, larger = more linear
    data: 'stars.6.json' // Data source for stellar data,
                         // number indicates limit magnitude
  },
  dsos: {
    show: true,    // Show Deep Space Objects
    limit: 6,      // Show only DSOs brighter than limit magnitude
    colors: true,  // // Show DSOs in symbol colors if true, use style setting below if false
    style: { fill: "#cccccc", stroke: "#cccccc", width: 2, opacity: 1 }, // Default style for dsos
    names: true,   // Show DSO names
    desig: true,   // Show short DSO names
    namestyle: { fill: "#cccccc", font: "11px Helvetica, Arial, serif",
                 align: "left", baseline: "top" }, // Style for DSO names
    namelimit: 6,  // Show only names for DSOs brighter than namelimit
    size: null,    // Optional seperate scale size for DSOs, null = stars.size
    exponent: 1.4, // Scale exponent for DSO size, larger = more non-linear
    data: 'dsos.bright.json', // Data source for DSOs,
                              // opt. number indicates limit magnitude
    symbols: {  //DSO symbol styles, 'stroke'-parameter present = outline
      gg: {shape: "circle", fill: "#ff0000"},          // Galaxy cluster
      g:  {shape: "ellipse", fill: "#ff0000"},         // Generic galaxy
      s:  {shape: "ellipse", fill: "#ff0000"},         // Spiral galaxy
      s0: {shape: "ellipse", fill: "#ff0000"},         // Lenticular galaxy
      sd: {shape: "ellipse", fill: "#ff0000"},         // Dwarf galaxy
      e:  {shape: "ellipse", fill: "#ff0000"},         // Elliptical galaxy
      i:  {shape: "ellipse", fill: "#ff0000"},         // Irregular galaxy
      oc: {shape: "circle", fill: "#ffcc00",
           stroke: "#ffcc00", width: 1.5},             // Open cluster
      gc: {shape: "circle", fill: "#ff9900"},          // Globular cluster
      en: {shape: "square", fill: "#ff00cc"},          // Emission nebula
      bn: {shape: "square", fill: "#ff00cc",
           stroke: "#ff00cc", width: 2},               // Generic bright nebula
      sfr:{shape: "square", fill: "#cc00ff",
           stroke: "#cc00ff", width: 2},               // Star forming region
      rn: {shape: "square", fill: "#00ooff"},          // Reflection nebula
      pn: {shape: "diamond", fill: "#00cccc"},         // Planetary nebula
      snr:{shape: "diamond", fill: "#ff00cc"},         // Supernova remnant
      dn: {shape: "square", fill: "#999999",
           stroke: "#999999", width: 2},               // Dark nebula grey
      pos:{shape: "marker", fill: "#cccccc",
           stroke: "#cccccc", width: 1.5}              // Generic marker
    }
  },
  planets: {  //Show planet locations, if date-time is set
    show: false,
    // List of all objects to show
    which: ["sol", "mer", "ven", "ter", "lun", "mar", "jup", "sat", "ura", "nep"],
    // Font styles for planetary symbols
    symbols: {  // Character and color for each symbol in 'which', simple circle \u25cf
      "sol": {symbol: "\u2609", letter:"Su", fill: "#ffff00"},
      "mer": {symbol: "\u263f", letter:"Me", fill: "#cccccc"},
      "ven": {symbol: "\u2640", letter:"V", fill: "#eeeecc"},
      "ter": {symbol: "\u2295", letter:"T", fill: "#00ccff"},
      "lun": {symbol: "\u25cf", letter:"L", fill: "#ffffff"}, // overridden by generated crecent, except letter
      "mar": {symbol: "\u2642", letter:"Ma", fill: "#ff6600"},
      "cer": {symbol: "\u26b3", letter:"C", fill: "#cccccc"},
      "ves": {symbol: "\u26b6", letter:"Ma", fill: "#cccccc"},
      "jup": {symbol: "\u2643", letter:"J", fill: "#ffaa33"},
      "sat": {symbol: "\u2644", letter:"Sa", fill: "#ffdd66"},
      "ura": {symbol: "\u2645", letter:"U", fill: "#66ccff"},
      "nep": {symbol: "\u2646", letter:"N", fill: "#6666ff"},
      "plu": {symbol: "\u2647", letter:"P", fill: "#aaaaaa"},
      "eri": {symbol: "\u26aa", letter:"E", fill: "#eeeeee"}
    },
    symbolStyle: { fill: "#00ccff", font: "bold 17px 'Lucida Sans Unicode', Consolas, sans-serif",
             align: "center", baseline: "middle" },
    symbolType: "symbol",  // Type of planet symbol: 'symbol' graphic planet sign, 'disk' filled circle scaled by magnitude
                           // 'letter': 1 or 2 letters S Me V L Ma J S U N
    names: false,          // Show name in nameType language next to symbol
    nameStyle: { fill: "#00ccff", font: "14px 'Lucida Sans Unicode', Consolas, sans-serif", align: "right", baseline: "top" },
    namesType: "desig"     // Language of planet name (see list below, ot all languages are available for planets,
                           // or desig = 3-letter designation
  },
  constellations: {
    names: false,      // Show constellation names
    namesType: "iau", // Type of name Latin (iau, default), 3 letter designation (desig) or other language (see list)
    nameStyle: { fill:"#cccc99", align: "center", baseline: "middle",
                 font: ["14px Helvetica, Arial, sans-serif",  // Style for constellations
                        "12px Helvetica, Arial, sans-serif",  // Different fonts for diff.
                        "11px Helvetica, Arial, sans-serif"]},// ranked constellations
    lines: false,   // Show constellation lines, style below
    lineStyle: { stroke: "#cccccc", width: 1, opacity: 0.6 },
    bounds: false, // Show constellation boundaries, style below
    boundStyle: { stroke: "#cccc00", width: 0.5, opacity: 0.8, dash: [2, 4] }
  },
  mw: {
    show: true,     // Show Milky Way as filled multi-polygon outlines
    style: { fill: "#cccccc", opacity: 0.15 }  // Style for MW layers
  },
  lines: {  // Display & styles for graticule & some planes
    graticule: { show: true, stroke: "#cccccc", width: 0.6, opacity: 0.8,
      // grid values: "outline", "center", or [lat,...] specific position
      lon: {pos: ["center"], fill: "#a6a6a6", font: "10px Helvetica, Arial, sans-serif"},
      // grid values: "outline", "center", or [lon,...] specific position
      lat: {pos: ["outline"], fill: "#a6a6a6", font: "10px Helvetica, Arial, sans-serif"}},
    equatorial: { show: true, stroke: "#aaaaaa", width: 1.3, opacity: 0.7 },
    ecliptic: { show: true, stroke: "#66cc66", width: 1.3, opacity: 0.7 },
    galactic: { show: false, stroke: "#cc6666", width: 1.3, opacity: 0.7 },
    supergalactic: { show: false, stroke: "#cc66cc", width: 1.3, opacity: 0.7 }
  },
  background: {        // Background style
    fill: "#fff",   // Area fill
    opacity: 1,
    stroke: "#000", // Outline
    width: 1
  },
  horizon: {  //Show horizon marker, if location is set and map projection is all-sky
    show: false,
    stroke: "#cccccc", // Line
    width: 1.0,
    fill: "#000000",   // Area below horizon
    opacity: 0.5
  },
  daylight: {  //Show day sky as a gradient, if location is set and map projection is hemispheric
    show: false
  }
};

// Asterisms canvas style properties for lines and text
var lineStyle = {
      stroke:"#f00",
      fill: "rgba(255, 204, 204, 0.4)",
      width: 3
    },
    textStyle = {
      fill:"#f00",
      font: "bold 15px Helvetica, Arial, sans-serif",
      align: "center",
      baseline: "middle"
    };

let jsonLine = JSON.parse(document.getElementById('skyregion-data').textContent);

Celestial.add({
  type:"line",

  callback: function(error, json) {

    if (error) return console.warn(error);
    // Load the geoJSON file and transform to correct coordinate system, if necessary
    var asterism = Celestial.getData(jsonLine, config.transform);

    // Add to celestial objects container in d3
    Celestial.container.selectAll(".asterisms")
      .data(asterism.features)
      .enter().append("path")
      .attr("class", "ast");
    // Trigger redraw to display changes
    Celestial.redraw();
  },

  redraw: function() {

    // Select the added objects by class name as given previously
    Celestial.container.selectAll(".ast").each(function(d) {
      // Set line styles
      Celestial.setStyle(lineStyle);
      // Project objects on map
      Celestial.map(d);
      // draw on canvas
      Celestial.context.fill();
      Celestial.context.stroke();

      // If point is visible (this doesn't work automatically for points)
      if (Celestial.clip(d.properties.loc)) {
        // get point coordinates
        let pt = Celestial.mapProjection(d.properties.loc);
        // Set text styles
        Celestial.setTextStyle(textStyle);
        // and draw text on canvas
        Celestial.context.fillText(d.properties.n, pt[0], pt[1]);
      }
    });
  }
});

// Display map with the configuration above or any subset thereof
Celestial.display(config);
