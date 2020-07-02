let conf_file = JSON.parse(document.getElementById('particlejs-conf-f').textContent);
/* particlesJS.load(@dom-id, @path-json, @callback (optional)); */
particlesJS.load('particles-js', conf_file, function() {
  console.log('callback - particles.js config loaded');
});
