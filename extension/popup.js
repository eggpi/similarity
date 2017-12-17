function renderPopUp(articles) {
  let container = document.getElementById("container");
  container.innerHTML = '<ol></ol>';
  for (let i = 0; i < articles.length; i++) {
    let li = document.createElement('li');
    let a = document.createElement('a');
    a.href = articles[i].url;
    a.target = '_blank';
    a.textContent = articles[i].title;
    li.appendChild(a);
    // li.appendChild(document.createTextNode(
    //  ' (' + articles[i].similarity + ')'));
    container.firstChild.appendChild(li);
  }
}

chrome.runtime.sendMessage({}, (articles) => {
  // https://bugs.chromium.org/p/chromium/issues/detail?id=428044
  setTimeout(() => { renderPopUp(articles); }, 100);
});
