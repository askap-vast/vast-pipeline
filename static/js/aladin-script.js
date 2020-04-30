let aladinConf = JSON.parse(document.getElementById('data-aladin').textContent);
var aladin = A.aladin('#aladinViz');
aladin.setZoom(aladinConf.aladin_zoom);
aladin.gotoPosition(aladinConf.aladin_ra , aladinConf.aladin_dec);
var sumss = aladin.createImageSurvey('SUMSS', 'SUMSS', 'https://alasky.u-strasbg.fr/SUMSS', 'equatorial', 6, {imgFormat: 'png'});
var nvss = aladin.createImageSurvey('NVSS', 'NVSS', 'https://alasky.u-strasbg.fr/NVSS/intensity/', 'equatorial', 5, {imgFormat: 'jpg'});
let survey = (aladinConf.aladin_dec < -40) ? sumss : nvss;
aladin.setImageSurvey(survey);
aladin.getBaseImageLayer().getColorMap().reverse();
if (aladinConf.hasOwnProperty('aladin_box_ra')) {
    var overlay = A.graphicOverlay({color: '#ee2345', lineWidth: 2});
    aladin.addOverlay(overlay);
    overlay.addFootprints([A.polygon([
        [aladinConf.aladin_ra + (aladinConf.aladin_box_ra / 2) , aladinConf.aladin_dec - (aladinConf.aladin_box_dec / 2)],
        [aladinConf.aladin_ra + (aladinConf.aladin_box_ra / 2) , aladinConf.aladin_dec + (aladinConf.aladin_box_dec / 2)],
        [aladinConf.aladin_ra - (aladinConf.aladin_box_ra / 2) , aladinConf.aladin_dec + (aladinConf.aladin_box_dec / 2)],
        [aladinConf.aladin_ra - (aladinConf.aladin_box_ra / 2) , aladinConf.aladin_dec - (aladinConf.aladin_box_dec / 2)],
    ])]);
}
