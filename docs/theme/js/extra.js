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
