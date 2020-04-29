let aladinConf = JSON.parse(document.getElementById('data-aladin').textContent);
var aladin = A.aladin('#aladinViz');
aladin.setZoom(aladinConf.aladin_zoom);
aladin.gotoPosition(aladinConf.aladin_ra , aladinConf.aladin_dec);
var sumss = aladin.createImageSurvey('SUMSS', 'SUMSS', 'https://alasky.u-strasbg.fr/SUMSS', 'equatorial', 6, {imgFormat: 'png'});
var nvss = aladin.createImageSurvey('NVSS', 'NVSS', 'https://alasky.u-strasbg.fr/NVSS/intensity/', 'equatorial', 5, {imgFormat: 'jpg'});
let survey = (aladinConf.aladin_dec < -40) ? sumss : nvss;
aladin.setImageSurvey(survey);
aladin.getBaseImageLayer().getColorMap().reverse();
