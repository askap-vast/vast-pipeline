function addGoToTop() {
  let toc = document.querySelectorAll('[aria-label="Table of contents"]');
  // only add the link if the TOC is on the page (it's the second one)
  if (toc.length > 1) {
    toc[1].innerHTML += '<a href="#top" id="gototop">Back to top</a>';
  }
}

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

/*
mkdocs-material loads local pages via XHR (they call it "instant loading") which speeds
up navigation by preventing a full page reload. This means that any custom JS is only
run on the first page load and skipped on subsequent loads. Below, we add functions
that should be called on each page load by subsribing them to the document$ observable,
i.e. any time the document changes, execute the following.
*/
// render MathJax
document$.subscribe(() => {
  MathJax.typesetPromise()
})

// configure images to use lightgallery
document$.subscribe(function() {
  var elements = document.getElementsByClassName("lightgallery");
  for(var i=0; i<elements.length; i++) {
     lightGallery(elements[i], {counter: false});
  }
})

// add a "Back to top" link to the TOC
document$.subscribe(() => {
  addGoToTop();
})
