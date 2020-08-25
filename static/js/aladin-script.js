let aladinConf = JSON.parse(document.getElementById('data-aladin').textContent);
var aladin = A.aladin('#aladinViz');
aladin.setZoom(aladinConf.aladin_zoom);
aladin.gotoPosition(aladinConf.aladin_ra , aladinConf.aladin_dec);
var sumss = aladin.createImageSurvey('SUMSS', 'SUMSS', 'https://alasky.u-strasbg.fr/SUMSS', 'equatorial', 6, {imgFormat: 'png'});
var nvss = aladin.createImageSurvey('NVSS', 'NVSS', 'https://alasky.u-strasbg.fr/NVSS/intensity/', 'equatorial', 5, {imgFormat: 'jpg'});
var racs = aladin.createImageSurvey('RACS', 'RACS', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/RACS_I1/', 'equatorial', 8, {imgFormat: 'png'});
var vast_epoch_01 = aladin.createImageSurvey(
    'VAST Pilot 1', 'VAST Pilot 1', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST1_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_02 = aladin.createImageSurvey(
    'VAST Pilot 2', 'VAST Pilot 2', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST2_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_03x = aladin.createImageSurvey(
    'VAST Pilot 3x', 'VAST Pilot 3x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST3x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_04x = aladin.createImageSurvey(
    'VAST Pilot 4x', 'VAST Pilot 4x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST4x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_05x = aladin.createImageSurvey(
    'VAST Pilot 5x', 'VAST Pilot 5x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST5x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_06x = aladin.createImageSurvey(
    'VAST Pilot 6x', 'VAST Pilot 6x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST6x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_07x = aladin.createImageSurvey(
    'VAST Pilot 7x', 'VAST Pilot 7x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST7x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_08 = aladin.createImageSurvey(
    'VAST Pilot 8', 'VAST Pilot 8', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST8_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_09 = aladin.createImageSurvey(
    'VAST Pilot 9', 'VAST Pilot 9', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST9_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_10x = aladin.createImageSurvey(
    'VAST Pilot 10', 'VAST Pilot 10x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST10x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
var vast_epoch_11x = aladin.createImageSurvey(
    'VAST Pilot 11x', 'VAST Pilot 11x', 'https://www.atnf.csiro.au/people/Emil.Lenc/HiPS/VAST11x_I4', 'equatorial', 6, {imgFormat: 'png'}
);
let survey = racs;
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
