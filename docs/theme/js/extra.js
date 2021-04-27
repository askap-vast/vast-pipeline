function addGoToTop() {
  document.querySelectorAll('[aria-label="Table of contents"]')[1].innerHTML += '<a href="#top" id="gototop">Back to top</a>';
}

// window.open = addGoToTop();
document.addEventListener('scroll', addGoToTop())

window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};

document$.subscribe(() => {
  MathJax.typesetPromise()
})

document$.subscribe(function() {
  var elements = document.getElementsByClassName("lightgallery");
  for(var i=0; i<elements.length; i++) {
     lightGallery(elements[i], {counter: false});
  }
})
