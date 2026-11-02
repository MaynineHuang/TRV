const toggle = document.getElementById('langToggle');
let language = 'en';
toggle.addEventListener('click', () => {
  language = language === 'en' ? 'zh' : 'en';
  document.documentElement.lang = language;
  document.querySelectorAll('[data-en][data-zh]').forEach((el) => { el.innerHTML = el.dataset[language]; });
  toggle.textContent = language === 'en' ? '中文 ↗' : 'EN ↗';
});

