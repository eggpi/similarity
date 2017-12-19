function renderWhitelistUI() {
  let whitelist = loadURLsWhitelist();
  let container = document.getElementById('domains-whitelist');
  container.innerHTML = '';
  whitelist.forEach((r, i) => {
    let entry = document.createElement('div');
    entry.classList.add('entry');

    let remove = document.createElement('img');
    remove.src = chrome.extension.getURL('icons/remove.svg');
    remove.classList.add('remove');
    entry.appendChild(remove);

    remove.addEventListener('click', () => {
      whitelist.splice(i, 1);
      saveURLsWhitelist(whitelist);
      renderWhitelistUI();
    });

    let label = document.createElement('span');
    label.textContent = r.toString();
    entry.appendChild(label);
    container.appendChild(entry);
  });
}

let regexpInput = document.getElementById('add-regexp-input');
regexpInput.addEventListener('input', () => {
  try {
    RegExp(regexpInput.value);
    regexpInput.setCustomValidity('');
  } catch (e) {
    regexpInput.setCustomValidity(
      'Invalid regular expression! ' + e.toString());
  }
  let whitelist = loadURLsWhitelist();
  if (whitelist.indexOf(regexpInput.value) > -1) {
    regexpInput.setCustomValidity(
      'This value is already whitelisted!');
  }
});

let regexpForm = document.getElementById('add-regexp');
regexpForm.addEventListener('submit', () => {
  let whitelist = loadURLsWhitelist();
  whitelist.push(regexpInput.value);
  whitelist.sort();
  saveURLsWhitelist(whitelist);
  renderWhitelistUI();
  return false;
});

let reset = document.getElementById('reset-whitelist');
reset.addEventListener('click', () => {
  saveURLsWhitelist(DEFAULT_WHITELISTED_URL_REGEXPS);
  renderWhitelistUI();
});

renderWhitelistUI();
