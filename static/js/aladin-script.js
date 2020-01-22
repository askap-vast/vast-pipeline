let aladinConf = JSON.parse(document.getElementById('data-aladin').textContent);
var aladin = A.aladin('#aladinViz');
aladin.setZoom(0.36);
aladin.gotoPosition(aladinConf.aladin_ra , aladinConf.aladin_dec);
var sumss = aladin.createImageSurvey('SUMSS', 'SUMSS', 'http://alasky.u-strasbg.fr/SUMSS', 'equatorial', 6, {imgFormat: 'png'});
var nvss = aladin.createImageSurvey('NVSS', 'NVSS', 'http://alasky.u-strasbg.fr/NVSS/intensity/', 'equatorial', 5, {imgFormat: 'jpg'});
aladin.setImageSurvey(sumss);
aladin.getBaseImageLayer().getColorMap().reverse();
